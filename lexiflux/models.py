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

    PRIVATE = "private"
    PUBLIC = "public"
    VISIBILITY_CHOICES = [
        (PRIVATE, "Private"),
        (PUBLIC, "Public"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_books",
    )

    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default=PRIVATE)
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

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    current_book = models.ForeignKey(
        Book, on_delete=models.SET_NULL, null=True, blank=True, related_name="current_readers"
    )
    native_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)


class ReadingProgress(models.Model):  # type: ignore
    """A reading progress."""

    reader = models.ForeignKey(
        ReaderProfile, on_delete=models.CASCADE, related_name="reading_progresses"
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    page_number = models.PositiveIntegerField()
    top_word_id = models.PositiveIntegerField()  # Assuming word ID is an integer

    last_read_time = models.DateTimeField(default=timezone.now)

    @classmethod
    def update_user_progress(
        cls, user: CustomUser, book_id: int, page_number: int, top_word_id: int
    ) -> None:
        """Update user reading progress."""
        reader_profile, _ = ReaderProfile.objects.get_or_create(user=user)

        # We search using user&book only but this is not enough to create a new record.
        # Thus we cannot use get_or_create.
        reading_progress = cls.objects.filter(
            reader=reader_profile, book_id=book_id
        ).first() or cls(reader=reader_profile, book_id=book_id)
        reading_progress.page_number = page_number
        reading_progress.top_word_id = top_word_id
        reading_progress.last_read_time = timezone.now()
        reading_progress.save()

    def get_books_ordered_by_last_read(self) -> models.QuerySet[Book]:
        """Return books ordered by last read time."""
        return (
            Book.objects.filter(reading_progresses__reader=self)
            .annotate(last_read_time=models.Max("reading_progresses__last_read_time"))
            .order_by("-last_read_time")
        )

    class Meta:
        """Meta class for ReadingProgress."""

        unique_together = ("reader", "book")


# todo: Reading history: for each reader I want history of hist navigation inside each book:
#  page number, time, word id
