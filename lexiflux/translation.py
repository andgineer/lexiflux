"""Translation module."""
from functools import lru_cache

from deep_translator import GoogleTranslator

from .models import Book, ReaderProfile


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
