"""Models for the lexiflux app."""
import json
import re
from typing import Any, Dict

from django.conf import settings
from django.db import models
from django.utils import timezone
from transliterate import get_available_language_codes, translit

from core.models import CustomUser


def split_into_words(text: str) -> list[str]:
    """Regular expression pattern to match words (ignores punctuation and spaces)."""
    stop_words = {"the"}
    pattern = re.compile(r"\b\w+\b")
    return [
        word.lower()
        for word in pattern.findall(text)
        if word.lower() not in stop_words and len(word) > 2
    ]


class Language(models.Model):  # type: ignore
    """Model to store languages."""

    google_code = models.CharField(max_length=10, unique=True)  # Google Translate language code
    epub_code = models.CharField(max_length=10)  # EPUB (ISO-639) language code

    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        """Return the string representation of a Language."""
        return self.name  # type: ignore


class Author(models.Model):  # type: ignore
    """An author of a book."""

    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        """Return the string representation of an Author."""
        return self.name  # type: ignore


class Book(models.Model):  # type: ignore
    """A book containing multiple pages."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_books",
    )

    code = models.CharField(max_length=100, unique=True)
    public = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="shared_books"
    )

    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    toc_json = models.TextField(null=True, blank=True, default="{}")

    @property
    def toc(self) -> Dict[str, Any]:
        """Property to automatically convert 'toc_json' to/from Python objects."""
        if self.toc_json:
            return json.loads(self.toc_json)  # type: ignore
        return {}

    @toc.setter
    def toc(self, value: Dict[str, Any]) -> None:
        """Set 'toc_json' when 'TOC' is updated."""
        self.toc_json = json.dumps(value)

    @property
    def current_reading_by_count(self) -> int:
        """Return the number of users currently reading this book."""
        return self.current_readers.count()  # type: ignore

    def generate_unique_book_code(self) -> str:
        """Generate a unique book code."""
        code = (
            "-".join(split_into_words(self.title)[:2])
            + "-"
            + split_into_words(self.author.name)[-1]
        )
        if self.language.google_code in get_available_language_codes():
            code = translit(code, self.language.google_code, reversed=True)

        unique_code = code
        counter = 1
        while Book.objects.filter(code=unique_code).exists():
            unique_code = f"{code}-{counter}"
            counter += 1

        return unique_code

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Generate book code and convert TOC."""
        if not self.code:
            self.code = self.generate_unique_book_code()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Return the string representation of a Book."""
        return self.title  # type: ignore


class BookFile(models.Model):  # type: ignore
    """Model to store original book files as blobs."""

    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name="original_file")
    file_blob = models.BinaryField()

    def __str__(self) -> str:
        """Return the string representation of a BookFile."""
        return f"Original file for {self.book.title}"


class BookPage(models.Model):  # type: ignore
    """A book page."""

    number = models.PositiveIntegerField()
    content = models.TextField()
    book = models.ForeignKey(Book, related_name="pages", on_delete=models.CASCADE)

    class Meta:
        """Meta class for BookPage."""

        ordering = ["number"]
        unique_together = ("book", "number")

    def __str__(self) -> str:
        """Return the string representation of a BookPage."""
        return f"Page {self.number} of {self.book.title}"


class ReaderProfile(models.Model):  # type: ignore
    """A reader profile."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reader_profile"
    )
    current_book = models.ForeignKey(
        Book, on_delete=models.SET_NULL, null=True, blank=True, related_name="current_readers"
    )
    native_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)


class ReadingPos(models.Model):  # type: ignore
    """A reading position.

    In History we store our breadcrumbs, so user can "undo" jumps by TOC or annotations.
    In position we store current reading position that may be not stored in History.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reading_pos"
    )
    book = models.ForeignKey("Book", on_delete=models.CASCADE)
    page_number = models.PositiveIntegerField()
    top_word_id = models.PositiveIntegerField()
    last_read_time = models.DateTimeField(default=timezone.now)
    latest_reading_point = models.CharField(
        max_length=50,
        default="0:0",
        help_text="Stores the latest reading point as 'page_number:top_word_id'",
    )

    @classmethod
    def update_user_pos(
        cls, user: CustomUser, book_id: int, page_number: int, top_word_id: int
    ) -> None:
        """Update user reading progress."""
        progress, created = cls.objects.get_or_create(
            user=user,
            book_id=book_id,
            defaults={
                "page_number": page_number,
                "top_word_id": top_word_id,
                "last_read_time": timezone.now(),
            },
        )

        if not created:
            progress.page_number = page_number
            progress.top_word_id = top_word_id
            progress.last_read_time = timezone.now()

            # Check and update the latest reading point
            current_latest_page, current_latest_word = map(
                int, progress.latest_reading_point.split(":")
            )
            if page_number > current_latest_page or (
                page_number == current_latest_page and top_word_id > current_latest_word
            ):
                progress.latest_reading_point = f"{page_number}:{top_word_id}"

            progress.save()

    class Meta:
        """Meta class for ReadingProgress."""

        unique_together = ("user", "book")


class ReadingHistory(models.Model):  # type: ignore
    """Model to store each reading session's details for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reading_history"
    )
    book = models.ForeignKey("Book", on_delete=models.CASCADE)
    page_number = models.PositiveIntegerField()
    top_word_id = models.PositiveIntegerField()
    read_time = models.DateTimeField(default=timezone.now)

    class Meta:
        """Meta class for ReadingHistory."""

        ordering = ["-read_time"]
