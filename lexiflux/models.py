"""Models for the lexiflux app."""
from django.conf import settings
from django.db import models


class Language(models.Model):  # type: ignore
    """Model to store languages."""

    code = models.CharField(max_length=10, unique=True)
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
    SHARED = "shared"
    PUBLIC = "public"
    VISIBILITY_CHOICES = [
        (PRIVATE, "Private"),
        (SHARED, "Shared"),
        (PUBLIC, "Public"),
    ]

    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default=PRIVATE)
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="shared_books"
    )

    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)

    @property
    def current_reading_by_count(self) -> int:
        """Return the number of users currently reading this book."""
        return self.current_readers.count()  # type: ignore

    def __str__(self) -> str:
        """Return the string representation of a Book."""
        return self.title  # type: ignore


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


class ReadingProgress(models.Model):  # type: ignore
    """A reading progress."""

    reader = models.ForeignKey(
        ReaderProfile, on_delete=models.CASCADE, related_name="reading_progresses"
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    page_number = models.PositiveIntegerField()
    top_word_id = models.PositiveIntegerField()  # Assuming word ID is an integer

    class Meta:
        """Meta class for ReadingProgress."""

        unique_together = ("reader", "book")
