"""Translation module."""

import logging
import os
from functools import lru_cache
from typing import Optional, List, Dict, Tuple

from deep_translator import (
    GoogleTranslator,
    MyMemoryTranslator,
    LingueeTranslator,
    PonsTranslator,
    single_detection,
)
from django.db.models import Q

from lexiflux.models import Language

log = logging.getLogger()

AVAILABLE_TRANSLATORS: Dict[str, Tuple[type, str]] = {
    "GoogleTranslator": (GoogleTranslator, "Google Translator"),
    "MyMemoryTranslator": (MyMemoryTranslator, "MyMemory Translator"),
    "LingueeTranslator": (LingueeTranslator, "Linguee Translator"),
    "PonsTranslator": (PonsTranslator, "PONS Translator"),
}


class Translator:
    """Translator."""

    def __init__(
        self, translator_name: str, source_language_code: str, target_language_code: str
    ) -> None:
        """Initialize Translator."""
        if translator_name not in AVAILABLE_TRANSLATORS:
            raise ValueError(f"Unsupported translator: {translator_name}")

        translator_class, _ = AVAILABLE_TRANSLATORS[translator_name]
        self._translator = translator_class(
            source=source_language_code, target=target_language_code
        )
        log.debug(
            "Translator: %s, source: %s, target %s",
            self._translator,
            source_language_code,
            target_language_code,
        )

    @lru_cache(maxsize=128)
    def translate(self, text: str) -> str:
        """Translate text."""
        return self._translator.translate(text)  # type: ignore

    @classmethod
    def available_translators(cls) -> List[Dict[str, str]]:
        """Return list of available translator names and labels."""
        return [
            {"value": name, "label": label} for name, (_, label) in AVAILABLE_TRANSLATORS.items()
        ]


@lru_cache(maxsize=128)
def get_translator(
    translator_name: str, source_language_code: str, target_language_code: str
) -> Translator:
    """Get translator."""
    return Translator(translator_name, source_language_code, target_language_code)


def detect_language(text: str) -> str:
    """Detect language."""
    log.debug("Fragment: %s", text)
    try:
        result = single_detection(text, api_key=os.environ["DETECTLANGUAGE_API_KEY"])
        log.debug("Detected language: %s", result)
        return result  # type: ignore
    except KeyError:
        log.error(
            "Please get you API Key at https://detectlanguage.com/documentation"
            " and set it to env var DETECTLANGUAGE_API_KEY"
        )
        return "en"
    except Exception as exc:  # pylint: disable=broad-except
        log.error("Failed to detect language: %s", exc)
        return "en"


def find_language(
    name: Optional[str] = None,
    google_code: Optional[str] = None,
    epub_code: Optional[str] = None,
) -> Optional[str]:
    """Find language.

    Find by provided parameters (which are not None).
    Return language name if found, None otherwise.
    """
    query = Q()
    if name:
        query |= Q(name=name)
    if google_code:
        query |= Q(google_code=google_code)
    if epub_code:
        query |= Q(epub_code=epub_code)

    language = Language.objects.filter(query).first()
    return language.name if language else None


if __name__ == "__main__":  # pragma: no cover
    print(detect_language("Dobar dan!"))
