"""Models for the lexiflux app."""

import json
import re
from typing import TypeAlias, Tuple, List, Any

from django.conf import settings
from django.db import models
from django.utils import timezone
from transliterate import get_available_language_codes, translit

from core.models import CustomUser

BOOK_CODE_LENGTH = 100

TocEntry: TypeAlias = Tuple[str, int, int]  # <title>, <page num>, <word on the page num>
Toc: TypeAlias = List[TocEntry]


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

    code = models.CharField(max_length=BOOK_CODE_LENGTH, unique=True)
    public = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="shared_books"
    )

    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    toc_json = models.TextField(null=True, blank=True, default="{}")

    @property
    def toc(self) -> Toc:
        """Property to automatically convert 'toc_json' to/from Python objects.

        (!) Serialization in JSON will return a list of lists instead of a list of tuples.
        We could convert them back here, but it has no practical benefit
        """
        return json.loads(self.toc_json) if self.toc_json else []  # type: ignore

    @toc.setter
    def toc(self, value: Toc) -> None:
        """Set 'toc_json' when 'TOC' is updated."""
        self.toc_json = json.dumps(value)

    @property
    def current_reading_by_count(self) -> int:
        """Return the number of users currently reading this book."""
        return self.current_readers.count()  # type: ignore

    def generate_unique_book_code(self) -> str:
        """Generate a unique book code."""
        code = (  # two words from title and last word of the author name (presumable last name)
            "-".join(split_into_words(self.title)[:2])
            + "-"
            + split_into_words(self.author.name)[-1]
        )
        # Transliterate the code to latin chars if the language is supported
        if self.language.google_code in get_available_language_codes():
            code = translit(code, self.language.google_code, reversed=True)

        # reserving 3 chars for the delimiter and two-digits counter in case the name is not unique
        code = code[: BOOK_CODE_LENGTH - 3]

        # Check if the code is unique, if not, append a counter
        unique_code = code
        counter = 1
        while Book.objects.filter(code=unique_code).exists():
            unique_code = f"{code}-{counter}"
            counter += 1

        return unique_code

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:  # Checks if the object already exists in the database
            original = Book.objects.get(pk=self.pk)
            if original.code:  # Checks if the original object has a code
                self.code = original.code  # Prevents the code from being changed
        elif not self.code:
            # This is a new object, so generate a unique code if it doesn't have one yet
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
    """A page of a book."""

    number = models.PositiveIntegerField()
    content = models.TextField()
    book = models.ForeignKey(Book, related_name="pages", on_delete=models.CASCADE)
    _words = models.JSONField(default=list, blank=True, db_column="words")

    class Meta:
        ordering = ["number"]
        unique_together = ("book", "number")

    def __str__(self) -> str:
        return f"Page {self.number} of {self.book.title}"

    @property
    def words(self) -> list[Tuple[int, int]]:
        """Property to parse words from the content."""
        if not self._words:
            self._words = self._parse_words()
            self.save(update_fields=["_words"])
        return self._words  # type: ignore

    @words.setter
    def words(self, value: list[Tuple[int, int]]) -> None:
        self._words = value

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.words:
            self.words = self._parse_words()
        super().save(*args, **kwargs)

    def _parse_words(self) -> list[Tuple[int, int]]:
        words = []
        for match in re.finditer(r"\S+", self.content):
            word = match.group()
            if word != "<br/>":
                words.append((match.start(), match.end()))
        return words


class ReaderProfile(models.Model):  # type: ignore
    """A reader profile."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reader_profile"
    )
    current_book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_readers",
    )
    native_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)


class ReadingLoc(models.Model):  # type: ignore
    """A reading location.

    Current reading location and the furthest reading location in the book.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reading_pos"
    )
    book = models.ForeignKey("Book", on_delete=models.CASCADE)
    page_number = models.PositiveIntegerField(help_text="Page number currently being read")
    word = models.PositiveIntegerField(help_text="Last word read on the current reading page")
    updated = models.DateTimeField(default=timezone.now)
    furthest_reading_page = models.PositiveIntegerField(
        default=0,
        help_text="Stores the furthest reading page number",
    )
    furthest_reading_word = models.PositiveIntegerField(
        default=0,
        help_text="Stores the furthest reading top word on the furthest page",
    )

    @classmethod
    def update_reading_location(
        cls, user: CustomUser, book_id: int, page_number: int, top_word_id: int
    ) -> None:
        """Update user reading progress."""
        location, created = cls.objects.get_or_create(
            user=user,
            book_id=book_id,
            defaults={
                "page_number": page_number,
                "word": top_word_id,
                "updated": timezone.now(),
            },
        )

        if not created:
            location.page_number = page_number
            location.word = top_word_id
            location.updated = timezone.now()

            # Check and update the latest reading point
            if page_number > location.furthest_reading_page or (
                page_number == location.furthest_reading_page
                and top_word_id > location.furthest_reading_page
            ):
                location.furthest_reading_page = page_number
                location.furthest_reading_word = top_word_id

            location.save()

    class Meta:
        """Meta class for ReadingProgress."""

        unique_together = ("user", "book")


class ReadingHistory(models.Model):  # type: ignore
    """Model to store each reading session's details for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reading_history",
    )
    book = models.ForeignKey("Book", on_delete=models.CASCADE)
    page_number = models.PositiveIntegerField()
    top_word_id = models.PositiveIntegerField()
    read_time = models.DateTimeField(default=timezone.now)

    class Meta:
        """Meta class for ReadingHistory."""

        ordering = ["-read_time"]
