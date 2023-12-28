"""Models for the lexiflux app."""
import json
from typing import Any, Dict

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import CustomUser


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

    public = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="shared_books"
    )

    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    toc = models.TextField(null=True, blank=True, default="{}")

    def set_toc(self, context_dict: Dict[str, Any]) -> None:
        """Set the context as a serialized JSON string."""
        self.toc = json.dumps(context_dict)

    def get_toc(self) -> Dict[str, Any]:
        """Get the context as a Python dictionary."""
        return json.loads(self.toc)  # type: ignore

    @property
    def current_reading_by_count(self) -> int:
        """Return the number of users currently reading this book."""
        return self.current_readers.count()  # type: ignore

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

    # todo: add latest reading point

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
