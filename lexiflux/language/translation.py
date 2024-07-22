"""Translation module."""

import logging
import os
from functools import lru_cache
from typing import Optional

from deep_translator import GoogleTranslator, single_detection
from django.db.models import Q

from lexiflux.models import Book, Language, LanguagePreferences

log = logging.getLogger()


class Translator:  # pylint: disable=too-few-public-methods
    """Translator."""

    def __init__(self, book: Book, language_preferences: LanguagePreferences) -> None:
        """Initialize Translator."""
        self._book = book
        self._profile = language_preferences
        source = book.language.google_code
        target = language_preferences.user_language.google_code
        print(f"The source is {source} and the target is {target}")
        self._translator = GoogleTranslator(source=source, target=target)

    @lru_cache(maxsize=128)
    def translate(self, text: str) -> str:
        """Translate text."""
        return self._translator.translate(text)  # type: ignore


@lru_cache(maxsize=128)
def get_translator(book: Book, language_preferences: LanguagePreferences) -> Translator:
    """Get translator."""
    return Translator(book, language_preferences)


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
