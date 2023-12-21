"""Translation module."""
import os
from functools import lru_cache
from typing import Optional

from deep_translator import GoogleTranslator, single_detection
from django.db.models import Q

from lexiflux.models import Book, Language, ReaderProfile


class Translator:  # pylint: disable=too-few-public-methods
    """Translator."""

    def __init__(self, book: Book, profile: ReaderProfile) -> None:
        """Initialize Translator."""
        self._book = book
        self._profile = profile
        source = "sr"
        target = "ru"
        self._translator = GoogleTranslator(source=source, target=target)

    @lru_cache(maxsize=128)
    def translate(self, text: str) -> str:
        """Translate text."""
        return self._translator.translate(text)  # type: ignore


@lru_cache(maxsize=128)
def get_translator(book_id: str, user_id: str) -> Translator:
    """Get translator."""
    book = Book.objects.get(id=book_id)
    profile = ReaderProfile.objects.get(user_id=user_id)
    return Translator(book, profile)


def detect_language(text: str) -> str:
    """Detect language."""
    return single_detection(text, api_key=os.getenv("DETECTLANGUAGE_API_KEY"))  # type: ignore


def find_language(
    name: Optional[str] = None, google_code: Optional[str] = None, epub_code: Optional[str] = None
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


if __name__ == "__main__":
    print(detect_language("Dobar dan!"))
