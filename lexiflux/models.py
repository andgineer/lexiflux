"""Models for the lexiflux app."""
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

    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)

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
