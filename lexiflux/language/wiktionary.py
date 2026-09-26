"""Wiktionary: senses for a word from the kaikki.org per-word pages."""

import json
import logging
import re
import time
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
from datetime import timedelta
from functools import cache
from typing import Any

import httpx
import simplemma
from django.apps import apps
from django.utils import timezone
from django.utils.html import escape, format_html, format_html_join
from django.utils.safestring import SafeString, mark_safe

from lexiflux.language.term_context import TERM_OPEN

log = logging.getLogger(__name__)

ENGLISH_EDITION = "en"
RUSSIAN_EDITION = "ru"
SERBO_CROATIAN = "sh"
CROATIAN = "hr"
GERMAN = "de"
# Wiktionary files Serbian, Croatian and Bosnian, and their translations, as Serbo-Croatian.
DATA_LANGUAGES = {"en": "en", "de": "de", "sr": "sh", "hr": "sh", "bs": "sh"}
DATA_LANGUAGE_NAMES = {"en": "English", "de": "German", "sh": "Serbo-Croatian"}
# Wiktionary files Norwegian translations also as Bokmål and Nynorsk, Filipino ones as Tagalog,
# most Chinese ones as Mandarin, and Kurdish ones (Google's "ku" is Kurmanji) as Kurmanji.
TRANSLATION_CODES = {
    "no": ("no", "nb", "nn"),
    "fil": ("fil", "tl"),
    "zh": ("zh", "cmn"),
    "ku": ("ku", "kmr"),
}
EDITION_URLS = {
    ENGLISH_EDITION: "https://kaikki.org/dictionary",
    RUSSIAN_EDITION: "https://kaikki.org/ruwiktionary",
}
# The Russian edition files Croatian apart from Serbian, in Latin script; Bosnian stays Serbian.
EDITION_LANGUAGE_NAMES = {
    ENGLISH_EDITION: {**DATA_LANGUAGE_NAMES, CROATIAN: DATA_LANGUAGE_NAMES[SERBO_CROATIAN]},
    RUSSIAN_EDITION: {
        "en": "Английский",
        "de": "Немецкий",
        "sh": "Сербский",
        CROATIAN: "Хорватский",
    },
}
LEMMATISER_LANGUAGES = {"en": "en", "de": "de", "sh": "hbs"}
# kaikki.org spells out the characters that are unsafe in its file names.
PAGE_NAME_ESCAPES = {
    ".": "_dot_",
    "/": "_slash_",
    "*": "_star_",
    "\\": "_backslash_",
    ":": "_colon_",
    "?": "_question_",
}
MAX_TITLE_BYTES = 255
USER_AGENT = "lexiflux (https://github.com/andgineer/lexiflux)"
REQUEST_SECONDS = 2.0
# The rest of the popup's 3 s is for rendering the answer and remembering it.
LOOKUP_SECONDS = 2.8
# Readers click words more than httpx's default 5 s apart; below nginx's default 75 s.
KEEPALIVE_SECONDS = 60
CACHE_DAYS = 30
MAX_FOLLOWED = 3
FETCH_THREADS = 8
FOLLOW_CANDIDATE = 2

LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
MAX_SENSES = 12
POS_LABELS = {
    "adj": "adjective",
    "adv": "adverb",
    "article": "article",
    "conj": "conjunction",
    "det": "determiner",
    "interj": "interjection",
    "intj": "interjection",
    "name": "proper noun",
    "noun": "noun",
    "num": "numeral",
    "particle": "particle",
    "phrase": "phrase",
    "prep": "preposition",
    "prep_phrase": "prepositional phrase",
    "pron": "pronoun",
    "verb": "verb",
    "unknown": "",
}
SKIPPED_POS = frozenset({"romanization", "character", "symbol"})
# Spellings nobody prints would drag unrelated lemmas in ("free" as a spelling of "three").
NOISE_TAGS = frozenset({"pronunciation-spelling", "misspelling", "eye-dialect"})
# Such a link leads to an unrelated word ("SHE" → health, dialectal "be" → by).
UNFOLLOWED_TAGS = NOISE_TAGS | {"dialectal", "initialism", "acronym"}

CARON = "̌"
ACUTE = "́"
GRAVE = "̀"
STRESS_MARKS = str.maketrans("", "", ACUTE + GRAVE)
EDGE_PUNCTUATION = ' \t\r\n.,;:!?"()[]{}«»„“”‚…—–'
# What precedes the first word of a sentence: nothing, or an end mark and quotes or dashes.
SENTENCE_START = re.compile(r"(?:^|[.!?…:])[\s\"'«»„“”‚‘’—–-]*$")
SERBIAN_CYRILLIC = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "ђ": "đ",
    "е": "e",
    "ж": "ž",
    "з": "z",
    "и": "i",
    "ј": "j",
    "к": "k",
    "л": "l",
    "љ": "lj",
    "м": "m",
    "н": "n",
    "њ": "nj",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "ћ": "ć",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "c",
    "ч": "č",
    "џ": "dž",
    "ш": "š",
}
CYRILLIC_TO_LATIN = str.maketrans(
    {
        **SERBIAN_CYRILLIC,
        **{char.upper(): latin.capitalize() for char, latin in SERBIAN_CYRILLIC.items()},
    },
)
LATIN_TO_CYRILLIC = {
    spelling: cyrillic
    for char, latin in SERBIAN_CYRILLIC.items()
    for spelling, cyrillic in (
        (latin, char),
        (latin.capitalize(), char.upper()),
        (latin.upper(), char.upper()),
    )
}
# Longest first, so "lj" is one letter, not two.
LATIN_LETTER = re.compile(
    "|".join(re.escape(spelling) for spelling in sorted(LATIN_TO_CYRILLIC, key=len, reverse=True)),
)


# Leading usage labels of Russian-edition senses ("экон.", "с.-х.", "мн. ч.", "устар. или поэт.");
# labels right before "от" are kept whole: "сокр. от ..." reads as "abbreviation of ...".
RUSSIAN_LABEL = r"[а-яё]+(?:\.-[а-яё]+)*\.(?:\s[а-яё]\.(?!-))*"
RUSSIAN_USAGE_LABELS = re.compile(
    rf"^(?:{RUSSIAN_LABEL}(?:\s+(?:и|или)\s+{RUSSIAN_LABEL})*(?:,\s*|\s+)(?![а-яё]\.(?!-)))+(?!от\s)",
)

_fetchers = ThreadPoolExecutor(max_workers=FETCH_THREADS, thread_name_prefix="kaikki")


class WiktionaryUnreachableError(Exception):
    pass


@dataclass(frozen=True)
class Sense:
    text: str
    note: str = ""


@dataclass(frozen=True)
class Entry:
    word: str
    pos: str
    edition: str
    language: str
    senses: tuple[Sense, ...]
    in_user_language: bool


@dataclass(frozen=True)
class PageEntry:
    word: str
    pos: str
    glosses: tuple[str, ...]
    translations: tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True)
class Page:
    entries: tuple[PageEntry, ...]
    links: tuple[str, ...]
    form_senses: tuple[tuple[str, str, str], ...]


def data_language(language_code: str) -> str | None:
    return DATA_LANGUAGES.get(language_code)


def wiktionary_code(language_code: str) -> str:
    code = language_code.split("-")[0].lower()
    return DATA_LANGUAGES.get(code, code)


def _strip_accents(text: str) -> str:
    # Wiktionary marks Serbo-Croatian pitch accents that books never print; č, š, ž, ć stay.
    kept: list[str] = []
    for char in unicodedata.normalize("NFD", text):
        if unicodedata.combining(char) and not (
            char == CARON or (char == ACUTE and kept and kept[-1] in "cC")
        ):
            continue
        kept.append(char)
    return unicodedata.normalize("NFC", "".join(kept))


def serbian_latin(text: str) -> str:
    return text.translate(CYRILLIC_TO_LATIN)


def serbian_cyrillic(text: str) -> str:
    return LATIN_LETTER.sub(lambda letter: LATIN_TO_CYRILLIC[letter.group()], text)


def lookup_key(text: str, language: str) -> str:
    key = " ".join(text.replace("’", "'").split()).lower()
    if language == SERBO_CROATIAN:
        key = serbian_latin(_strip_accents(key))
    return key


def page_word(word: str, section: str, edition: str) -> str:
    # Serbian: the English edition files Latin spellings; the Russian edition's Cyrillic pages
    # are fuller than its Latin ones.
    if section == CROATIAN:
        return serbian_latin(word)
    if section != SERBO_CROATIAN:
        return word
    latin = serbian_latin(word)
    return latin if edition == ENGLISH_EDITION else serbian_cyrillic(latin)


def kaikki_url(edition: str, section: str, word: str) -> str:
    name = "".join(PAGE_NAME_ESCAPES.get(char, char) for char in word)
    path = f"{name[0]}/{name[:2]}/{name}"
    language_name = EDITION_LANGUAGE_NAMES[edition][section]
    return (
        f"{EDITION_URLS[edition]}/{urllib.parse.quote(language_name)}/meaning/"
        f"{urllib.parse.quote(path)}.jsonl"
    )


def _translations(
    record: dict[str, Any],
    user_language: str,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    by_sense: dict[str, list[str]] = {}
    codes = TRANSLATION_CODES.get(user_language, (user_language,))
    for translation in record.get("translations", []):
        code = translation.get("lang_code") or translation.get("code")
        if code in codes and translation.get("word"):
            by_sense.setdefault(translation.get("sense") or "", []).append(translation["word"])
    return tuple((sense, tuple(dict.fromkeys(words))) for sense, words in by_sense.items())


def prune(record: dict[str, Any], edition: str, user_language: str) -> PageEntry | None:
    word, pos = record.get("word"), record.get("pos")
    if not word or not pos or pos in SKIPPED_POS:
        return None
    glosses: list[str] = []
    for sense in record.get("senses", []):
        if NOISE_TAGS.intersection(sense.get("tags", [])):
            continue
        links = sense.get("form_of", []) + sense.get("alt_of", [])
        if not any(link.get("word") for link in links) and sense.get("glosses"):
            # English-edition sub-senses repeat their parents' glosses first.
            glosses.append(sense["glosses"][-1])
    translations = _translations(record, user_language) if edition == ENGLISH_EDITION else ()
    if not glosses and not translations:
        return None
    return PageEntry(word, pos, tuple(dict.fromkeys(glosses)), translations)


def _followed_links(sense: dict[str, Any]) -> list[str]:
    # Inflections, also archaic ones ("liveth" → live), and contractions ("I'm" → I).
    tags = set(sense.get("tags", []))
    contraction = "contraction" in tags
    if tags & UNFOLLOWED_TAGS or ("abbreviation" in tags and not contraction):
        return []
    links = sense.get("form_of", []) + (sense.get("alt_of", []) if contraction else [])
    return [link["word"] for link in links if link.get("word")]


def parse_page(text: str, edition: str, user_language: str) -> Page:
    records = [json.loads(line) for line in text.splitlines() if line.startswith("{")]
    if not records:
        # A page, but not kaikki.org's JSON lines: a changed site, not a missing word.
        raise WiktionaryUnreachableError("the page has no JSON lines")
    entries: list[PageEntry] = []
    links: list[str] = []
    form_senses: list[tuple[str, str, str]] = []
    try:
        for record in records:
            if entry := prune(record, edition, user_language):
                entries.append(entry)
            for sense in record.get("senses", []):
                if targets := _followed_links(sense):
                    links.extend(targets)
                    if sense.get("glosses"):
                        form_senses.append(
                            (record.get("word", ""), record.get("pos", ""), sense["glosses"][-1]),
                        )
    except (AttributeError, TypeError) as e:
        # A record of another shape ("senses": null) is a changed site, like a page without JSON.
        raise WiktionaryUnreachableError(f"unexpected record: {e}") from e
    return Page(tuple(entries), tuple(dict.fromkeys(links)), tuple(form_senses))


def _load_page(data: dict[str, Any]) -> Page:
    return Page(
        entries=tuple(
            PageEntry(
                entry["word"],
                entry["pos"],
                tuple(entry["glosses"]),
                tuple((note, tuple(words)) for note, words in entry["translations"]),
            )
            for entry in data["entries"]
        ),
        links=tuple(data["links"]),
        form_senses=tuple((word, pos, gloss) for word, pos, gloss in data["form_senses"]),
    )


@cache
def http_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        limits=httpx.Limits(keepalive_expiry=KEEPALIVE_SECONDS),
    )


def _download(
    client: httpx.Client,
    url: str,
    edition: str,
    user_language: str,
    timeout: float,
) -> Page | None:
    response = client.get(url, timeout=timeout)
    if response.status_code == httpx.codes.NOT_FOUND:
        return None
    if response.status_code != httpx.codes.OK:
        raise WiktionaryUnreachableError(f"HTTP {response.status_code}")
    return parse_page(response.text, edition, user_language)


def _page_cache() -> Any:
    return apps.get_model("lexiflux", "WiktionaryPage").objects


def _cached_pages(urls: list[str], user_language: str) -> dict[str, Page | None]:
    rows = _page_cache().filter(
        url__in=urls,
        user_language=user_language,
        fetched__gte=timezone.now() - timedelta(days=CACHE_DAYS),
    )
    return {
        url: None if content is None else _load_page(content)
        for url, content in rows.values_list("url", "content")
    }


def _cache_pages(pages: dict[str, Page | None], user_language: str) -> None:
    if not pages:
        return
    cache_rows = _page_cache()
    now = timezone.now()
    cache_rows.bulk_create(
        [
            cache_rows.model(
                url=url,
                user_language=user_language,
                content=None if page is None else asdict(page),
                fetched=now,
            )
            for url, page in pages.items()
        ],
        update_conflicts=True,
        unique_fields=["url", "user_language"],
        update_fields=["content", "fetched"],
    )
    cache_rows.filter(fetched__lt=now - timedelta(days=CACHE_DAYS)).delete()


class _Pages:
    def __init__(self, language: str, section: str, user_language: str) -> None:
        self.language = language
        self.section = section
        self.user_language = user_language
        # Russian glosses help only a Russian reader; the English edition serves everyone.
        self.editions = [ENGLISH_EDITION]
        if user_language == RUSSIAN_EDITION:
            self.editions.insert(0, RUSSIAN_EDITION)
        self.deadline = time.monotonic() + LOOKUP_SECONDS
        self.failed = False

    def fetch(self, words: list[str], first_candidate: int) -> list[tuple[int, str, Page]]:
        requests: list[tuple[int, str, str]] = []
        for index, word in enumerate(words):
            for edition in self.editions:
                spelling = page_word(word, self.section, edition)
                # No Wiktionary title is longer, so such a selection has no page.
                if len(spelling.encode()) <= MAX_TITLE_BYTES:
                    url = kaikki_url(edition, self.section, spelling)
                    requests.append((first_candidate + index, edition, url))
        pages = _cached_pages([url for *_, url in requests], self.user_language)
        fresh = self._download({url: edition for _, edition, url in requests if url not in pages})
        _cache_pages(fresh, self.user_language)
        pages |= fresh
        return [
            (candidate, edition, page)
            for candidate, edition, url in requests
            if (page := pages.get(url)) is not None
        ]

    def _download(self, editions: dict[str, str]) -> dict[str, Page | None]:
        timeout = min(REQUEST_SECONDS, self.deadline - time.monotonic())
        if not editions:
            return {}
        if timeout <= 0:
            self.failed = True
            return {}
        client = http_client()
        futures = {
            url: _fetchers.submit(_download, client, url, edition, self.user_language, timeout)
            for url, edition in editions.items()
        }
        wait(futures.values(), timeout=max(0.0, self.deadline - time.monotonic()))
        pages: dict[str, Page | None] = {}
        for url, future in futures.items():
            if not future.done():
                future.cancel()
                log.warning("kaikki.org: no answer in time for %s", url)
                self.failed = True
                continue
            try:
                pages[url] = future.result()
            except (httpx.HTTPError, WiktionaryUnreachableError, ValueError) as e:
                log.warning("kaikki.org: %s failed: %s", url, e)
                self.failed = True
        return pages


def _spelling(word: str, language: str) -> str:
    # German page names differ by case ("Tanzen" is not "tanzen"); elsewhere case is incidental.
    return word if language == GERMAN else lookup_key(word, language)


def _words(typed: str, language: str) -> list[str]:
    # A capital marks a German noun ("Schloss", not "schloss" of "schließen"); elsewhere it is
    # mostly a sentence start.
    surface = typed if language == GERMAN else typed.lower()
    if " " in surface:
        return [surface]
    # simplemma knows more Serbian forms in Latin script ("protiče" → "proticati", not "протиче").
    source = serbian_latin(surface) if language == SERBO_CROATIAN else surface
    lemma = simplemma.lemmatize(source, lang=LEMMATISER_LANGUAGES[language], low_memory=True)
    # simplemma capitalises some lowercase words ("robin" → "Robin"); "I" must keep its capital.
    if lemma == source or (
        typed[:1].islower() and lookup_key(lemma, language) == lookup_key(surface, language)
    ):
        lemma = surface
    words = {_spelling(word, language): word for word in (surface, lemma)}
    return list(words.values())


def _entry(item: PageEntry, edition: str, language: str, user_language: str) -> Entry:
    if item.translations:
        senses = tuple(Sense(", ".join(words), note) for note, words in item.translations)
    else:
        senses = tuple(Sense(gloss) for gloss in item.glosses)
    return Entry(
        word=item.word,
        pos=item.pos,
        edition=edition,
        language=language,
        senses=senses,
        in_user_language=bool(item.translations) or edition == user_language,
    )


def _rank(
    found: list[tuple[int, str, Page]],
    wanted: str,
    pages: _Pages,
    names: bool = False,
    written: int = 0,
) -> list[Entry]:
    groups: dict[int, dict[int, list[tuple[int, Entry]]]] = {}
    index = 0
    for candidate, edition, page in found:
        for item in page.entries:
            index += 1
            # A name reached through a lemma or a link is mostly a surname ("august" → "August").
            if item.pos == "name" and candidate not in (0, written) and not names:
                continue
            if (entry := _entry(item, edition, pages.language, pages.user_language)).senses:
                by_edition = groups.setdefault(candidate, {})
                by_edition.setdefault(pages.editions.index(edition), []).append((index, entry))
    ranked: list[tuple[bool, int, int, list[Entry]]] = []
    for candidate, by_edition in groups.items():
        candidate_entries: list[Entry] = []
        for edition in sorted(by_edition):
            items = by_edition[edition]
            items.sort(
                key=lambda item: (
                    not item[1].in_user_language,
                    item[1].pos == "name",
                    item[1].word != wanted,
                    item[0],
                ),
            )
            candidate_entries.extend(entry for _, entry in items)
        # More senses usually means a more common word: "made" is "make" before it is a maggot.
        other_case = all(
            entry.word[:1].isupper() != wanted[:1].isupper() for entry in candidate_entries
        )
        senses = sum(len(entry.senses) for entry in candidate_entries)
        ranked.append((other_case, -senses, candidate, candidate_entries))
    return [entry for *_, candidate_entries in sorted(ranked) for entry in candidate_entries]


def _form_entries(page: Page, language: str) -> list[Entry]:
    glosses: dict[tuple[str, str], list[str]] = {}
    for word, pos, gloss in page.form_senses:
        glosses.setdefault((word, pos), []).append(gloss)
    return [
        Entry(
            word=word,
            pos=pos,
            edition=ENGLISH_EDITION,
            language=language,
            senses=tuple(Sense(gloss) for gloss in dict.fromkeys(word_glosses)),
            in_user_language=False,
        )
        for (word, pos), word_glosses in glosses.items()
    ]


def _with_links(
    pages: _Pages,
    words: list[str],
    first_round: list[tuple[int, str, Page]],
    entries: list[Entry],
    wanted: str,
) -> list[Entry]:
    # Contractions and archaic forms that the lemmatiser leaves as they are ("I'm", "liveth").
    own_page = next(
        (
            page
            for candidate, edition, page in first_round
            if candidate == 0 and edition == ENGLISH_EDITION
        ),
        None,
    )
    if own_page is None:
        return entries
    known = {_spelling(word, pages.language) for word in words}
    followed = [link for link in own_page.links if _spelling(link, pages.language) not in known]
    if not followed:
        return entries
    linked = pages.fetch(followed[:MAX_FOLLOWED], FOLLOW_CANDIDATE)
    return entries + _form_entries(own_page, pages.language) + _rank(linked, wanted, pages)


def sentence_start(passage: str) -> bool | None:
    if TERM_OPEN not in passage:
        return None
    return bool(SENTENCE_START.search(passage.split(TERM_OPEN, 1)[0]))


def _translated(found: list[tuple[int, str, Page]], candidate: int) -> bool:
    return any(
        item.translations
        for number, _, page in found
        if number == candidate
        for item in page.entries
    )


def _typed(text: str, language: str) -> str:
    typed = " ".join(text.strip(EDGE_PUNCTUATION).replace("’", "'").split())
    # Accented text ("kȍsu") has no page of its own; Wiktionary's page names are unaccented.
    return _strip_accents(typed) if language == SERBO_CROATIAN else typed


def _written(typed: str, words: list[str], pages: _Pages, start: bool | None) -> bool:
    # A capital in mid-sentence marks a name ("China"); it may share its letters with a
    # lowercase word ("china").
    page = page_word(typed, pages.section, ENGLISH_EDITION)
    return (
        pages.language != GERMAN
        and typed[:1].isupper()
        and start is False
        and all(page_word(word, pages.section, ENGLISH_EDITION) != page for word in words)
    )


def _wanted(
    typed: str,
    pages: _Pages,
    start: bool | None,
    first_round: list[tuple[int, str, Page]],
    written: int,
) -> str:
    if pages.language == GERMAN:
        # A capital at a sentence start does not make a word a noun ("Ich", not "das Ich").
        return typed.lower() if start else typed
    if written and (pages.language == SERBO_CROATIAN or _translated(first_round, written)):
        # An English name without translations is mostly a surname, or a personified "King".
        return typed
    return typed.lower()


def _with_lowercase(
    pages: _Pages,
    typed: str,
    start: bool | None,
    candidates: list[str],
    entries: list[Entry],
) -> list[Entry]:
    # A German capital at a sentence start ("Gut, dass ..."), or on a word found only as a name
    # ("Schön"), does not make it a noun.
    if (
        pages.failed
        or pages.language != GERMAN
        or not typed[:1].isupper()
        or not all(entry.word[:1].isupper() if start else entry.pos == "name" for entry in entries)
    ):
        return entries
    lower = typed.lower()
    lower_words = [word for word in _words(lower, pages.language) if word not in candidates]
    if not lower_words:
        return entries
    lowered = _rank(pages.fetch(lower_words, 0), lower, pages)
    # "schloss" is only a form of "schließen": "Schloss" still starts with the noun.
    if entries and not any(entry.word == lower for entry in lowered):
        return entries + lowered
    return lowered + entries


def lookup(
    text: str,
    language_code: str,
    user_language_code: str,
    passage: str = "",
) -> list[Entry]:
    language = data_language(language_code)
    if language is None:
        return []
    typed = _typed(text, language)
    if not typed:
        return []
    section = CROATIAN if language_code == CROATIAN else language
    pages = _Pages(language, section, wiktionary_code(user_language_code))
    start = sentence_start(passage)
    words = _words(typed, language)
    written = len(words) if _written(typed, words, pages, start) else 0
    candidates = [*words, typed] if written else words
    first_round = pages.fetch(candidates, 0)
    wanted = _wanted(typed, pages, start, first_round, written)
    entries = _rank(first_round, wanted, pages, written=written)
    if len(words) == 1:
        entries = _with_links(pages, words, first_round, entries, wanted)
    if not entries:
        # An inflected name ("Beogradu" → "Beograd") has only its lemma's name entries.
        entries = _rank(first_round, wanted, pages, names=True, written=written)
    if not pages.failed and not entries and typed not in candidates:
        # A name: nothing is written like it in lower case ("London").
        entries = _rank(pages.fetch([typed], 0), typed, pages)
    entries = _with_lowercase(pages, typed, start, candidates, entries)
    if not entries and pages.failed:
        raise WiktionaryUnreachableError(typed)
    return entries


def _text(text: str) -> SafeString:
    # The sidebar applies *emphasis* markdown to its HTML; a literal star must not trigger it.
    return mark_safe(escape(text).replace("*", "&#42;"))  # noqa: S308


def _sense_html(sense: Sense) -> SafeString:
    if sense.note:
        return format_html(
            '{} <span class="wiktionary-note text-muted">({})</span>',
            _text(sense.text),
            _text(sense.note),
        )
    return _text(sense.text)


def _entry_html(entry: Entry) -> SafeString:
    senses = format_html_join(
        "",
        "<li>{}</li>",
        ((_sense_html(sense),) for sense in entry.senses[:MAX_SENSES]),
    )
    return format_html(
        '<div class="wiktionary-entry"><span class="wiktionary-word fw-bold">{}</span> '
        '<span class="wiktionary-pos fst-italic">{}</span>'
        '<ol class="wiktionary-senses mb-1">{}</ol></div>',
        _text(entry.word),
        _text(POS_LABELS.get(entry.pos, entry.pos)),
        senses,
    )


def page_url(entry: Entry) -> str:
    url = f"https://{entry.edition}.wiktionary.org/wiki/{urllib.parse.quote(entry.word)}"
    if entry.edition == ENGLISH_EDITION:
        url += "#" + DATA_LANGUAGE_NAMES[entry.language].replace(" ", "_")
    return url


def render(entries: list[Entry]) -> SafeString:
    return format_html(
        '<div class="wiktionary"><div class="wiktionary-entries">{}</div>'
        '<div class="wiktionary-attribution small text-muted">'
        'from <a href="{}" target="_blank" rel="noopener">Wiktionary</a>, '
        '<a href="{}" target="_blank" rel="noopener">CC BY-SA 4.0</a></div></div>',
        format_html_join("", "{}", ((_entry_html(entry),) for entry in entries)),
        page_url(entries[0]),
        LICENSE_URL,
    )


def summary(entries: list[Entry]) -> str:
    entry = next((entry for entry in entries if entry.in_user_language), entries[0])
    text = entry.senses[0].text
    if entry.edition == RUSSIAN_EDITION:
        text = RUSSIAN_USAGE_LABELS.sub("", text) or text
    # Stress marks help in the sense list; the vocabulary export wants the plain word.
    return text.translate(STRESS_MARKS)
