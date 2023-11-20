"""Models for the Lexiflux app.""" ""
from django.db import models


class BookPage(models.Model):  # type: ignore
    """A book page."""

    number = models.PositiveIntegerField()
    content = models.TextField()

    class Meta:
        """Meta options for BookPage."""

        ordering = ["number"]

    def __str__(self) -> str:
        """Return the string representation of a BookPage."""
        return str(self.number)
