"""Translation module."""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from django.utils.safestring import SafeString

from lexiflux.language import wiktionary
from lexiflux.language.llm import InlineTranslationRequest, translate_inline

log = logging.getLogger()

GOOGLE_LANGUAGES_FILE = (
    Path(__file__).resolve().parent.parent / "resources" / "google_translate_languages.json"
)
GOOGLE_URL = "https://translate.googleapis.com/translate_a/single"
# Google blocks an identifier without notice; the next one usually still answers.
GOOGLE_CLIENTS = ("dict-chrome-ex", "gtx", "at")
GOOGLE_BLOCKED_STATUSES = frozenset({403, 429})
GOOGLE_TIMEOUT_SECONDS = 3.0
GOOGLE_MAX_URL_LENGTH = 16384
GOOGLE_TERMS_PER_PART_OF_SPEECH = 8
WORD_CACHE_SIZE = 128
GOOGLE_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0 Safari/537.36"
)


class TranslatorError(Exception):
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"
    TOO_LONG = "too_long"
    NOT_INSTALLED = "not_installed"

    def __init__(self, kind: str, detail: str = "") -> None:
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind = kind


@dataclass(frozen=True)
class Term:
    word: str
    # The word marked in its sentence and the neighbouring ones; only the LLM reads it.
    passage: str = ""
    user: Any = field(default=None, compare=False, hash=False)


@dataclass(frozen=True)
class HtmlTranslation:
    """Trusted HTML: the translator escaped every dictionary text while building it."""

    html: SafeString
    translation: str


@dataclass(frozen=True)
class GoogleTranslation:
    translation: str
    alternatives: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def text(self) -> str:
        lines = [self.translation]
        for part_of_speech, terms in self.alternatives:
            joined = ", ".join(terms)
            lines.append(f"*{part_of_speech}:* {joined}" if part_of_speech else joined)
        return "\n".join(lines)


@lru_cache(maxsize=1)
def google_language_codes() -> dict[str, str]:
    languages = json.loads(GOOGLE_LANGUAGES_FILE.read_text(encoding="utf8"))["languages"]
    return {language["name"].lower(): language["id"] for language in languages}


def google_code(language: str) -> str:
    codes = google_language_codes()
    if language in codes.values():
        return language
    if code := codes.get(language.lower()):
        return code
    raise TranslatorError(TranslatorError.UNSUPPORTED, language)


def _google_alternatives(entries: Any) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if not isinstance(entries, list):
        return ()
    return tuple(
        (entry[0] or "", tuple(entry[1][:GOOGLE_TERMS_PER_PART_OF_SPEECH]))
        for entry in entries
        if isinstance(entry, list) and len(entry) > 1 and isinstance(entry[1], list) and entry[1]
    )


def parse_google_answer(data: Any, text: str) -> GoogleTranslation:
    if not isinstance(data, list) or not data or not isinstance(data[0], list):
        raise TranslatorError(TranslatorError.NOT_FOUND)
    translation = "".join(
        segment[0]
        for segment in data[0]
        if isinstance(segment, list) and segment and isinstance(segment[0], str)
    ).strip()
    alternatives = _google_alternatives(data[1] if len(data) > 1 else None)
    # Google echoes a word it cannot translate.
    echo = translation.casefold() == text.strip().casefold()
    if not translation or (echo and not alternatives):
        raise TranslatorError(TranslatorError.NOT_FOUND)
    return GoogleTranslation(translation, alternatives)


class GoogleTranslator:
    def __init__(
        self,
        source: str,
        target: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.source = google_code(source)
        self.target = google_code(target)
        self._http = httpx.Client(
            headers={"User-Agent": GOOGLE_USER_AGENT},
            transport=transport,
        )
        self._cached_lookup = lru_cache(maxsize=WORD_CACHE_SIZE)(self.lookup)

    def translate(self, term: Term) -> str:
        return self._cached_lookup(term.word).text()

    def lookup(self, text: str) -> GoogleTranslation:
        deadline = time.monotonic() + GOOGLE_TIMEOUT_SECONDS
        for client in GOOGLE_CLIENTS:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            request = self._http.build_request(
                "GET",
                GOOGLE_URL,
                params=[
                    ("client", client),
                    ("sl", self.source),
                    ("tl", self.target),
                    ("dt", "t"),
                    ("dt", "bd"),
                    ("q", text),
                ],
                timeout=remaining,
            )
            if len(str(request.url)) > GOOGLE_MAX_URL_LENGTH:
                raise TranslatorError(TranslatorError.TOO_LONG)
            try:
                response = self._http.send(request)
            except httpx.HTTPError as e:
                raise TranslatorError(TranslatorError.NETWORK, type(e).__name__) from e
            if response.status_code in GOOGLE_BLOCKED_STATUSES:
                log.warning("Google client %s refused: HTTP %s", client, response.status_code)
                continue
            if response.is_error:
                raise TranslatorError(TranslatorError.NETWORK, f"HTTP {response.status_code}")
            try:
                data = response.json()
            except ValueError:
                log.warning("Google client %s answered with non-JSON", client)
                continue
            return parse_google_answer(data, text)
        raise TranslatorError(TranslatorError.RATE_LIMIT, "every identifier tried refused")


class WiktionaryTranslator:
    def __init__(self, source: str, target: str) -> None:
        self.source = google_code(source)
        self.target = google_code(target)
        if wiktionary.data_language(self.source) is None:
            raise TranslatorError(TranslatorError.UNSUPPORTED, source)

    def translate(self, term: Term) -> HtmlTranslation:
        try:
            entries = wiktionary.lookup(term.word, self.source, self.target)
        except wiktionary.WiktionaryNotInstalledError as e:
            raise TranslatorError(TranslatorError.NOT_INSTALLED, str(e)) from e
        if not entries:
            raise TranslatorError(TranslatorError.NOT_FOUND)
        return HtmlTranslation(wiktionary.render(entries), wiktionary.summary(entries))


class LLMTranslator:
    def __init__(self, source: str, target: str) -> None:
        self.source = source
        self.target = target

    def translate(self, term: Term) -> str:
        return translate_inline(
            InlineTranslationRequest(
                word=term.word,
                passage=term.passage,
                text_language=self.source,
                user_language=self.target,
                user=term.user,
            ),
        )


AVAILABLE_TRANSLATORS: dict[str, tuple[Callable[..., Any], str]] = {
    "LLMTranslation": (LLMTranslator, "LLM translation"),
    "Wiktionary": (WiktionaryTranslator, "Wiktionary"),
    "Google": (GoogleTranslator, "Google"),
}


class Translator:
    """Translator."""

    def __init__(
        self,
        translator_name: str,
        source_language: str,
        target_language: str,
    ) -> None:
        """Initialize Translator."""
        if translator_name not in AVAILABLE_TRANSLATORS:
            raise ValueError(f"Unsupported translator: {translator_name}")

        translator_class, _ = AVAILABLE_TRANSLATORS[translator_name]
        self._translator = translator_class(source=source_language, target=target_language)
        log.debug(
            "Translator: %s, source: %s, target %s",
            self._translator,
            source_language,
            target_language,
        )

    def translate(self, term: Term) -> str | HtmlTranslation:
        return self._translator.translate(term)

    @classmethod
    def available_translators(cls) -> list[dict[str, str]]:
        """Return list of available translator names and labels."""
        return [
            {"value": name, "label": label} for name, (_, label) in AVAILABLE_TRANSLATORS.items()
        ]


@lru_cache(maxsize=128)
def get_translator(
    translator_name: str,
    source_language: str,
    target_language: str,
) -> Translator:
    """Get translator."""
    return Translator(translator_name, source_language, target_language)
