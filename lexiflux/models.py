"""Models for the lexiflux app."""

import json
import re
from typing import TypeAlias, Tuple, List, Any, Dict, Optional

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from transliterate import get_available_language_codes, translit

from lexiflux.language.sentence_extractor import break_into_sentences
from lexiflux.language.word_extractor import parse_words

BOOK_CODE_LENGTH = 100

ARTICLE_TYPES = [
    ("Translate", "Translate"),
    ("Sentence", "Sentence"),
    ("Explain", "Explain"),
    ("Examples", "Examples"),
    ("Lexical", "Lexical"),
    ("Dictionary", "Dictionary"),
    ("Site", "Site"),
]

TocEntry: TypeAlias = Tuple[str, int, int]  # <title>, <page num>, <word on the page num>
Toc: TypeAlias = List[TocEntry]


class CustomUser(AbstractUser):  # type: ignore
    """Custom user model for the application."""

    email = models.EmailField(unique=True, blank=False)
    is_approved = models.BooleanField(default=False)

    default_language_preferences = models.ForeignKey(
        "lexiflux.LanguagePreferences",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_users",
    )


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

    google_code = models.CharField(
        max_length=10, primary_key=True
    )  # Google Translate language code
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

    code = models.CharField(max_length=BOOK_CODE_LENGTH, unique=True, db_index=True)
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
    book = models.ForeignKey("Book", related_name="pages", on_delete=models.CASCADE)
    word_indices = models.TextField(
        null=True,
        blank=True,
        help_text="Word indices in JSON format. List of tuples with start and end index. "
        "Index in the list - word index.",
    )
    word_to_sentence_map = models.JSONField(null=True, blank=True)

    _word_sentence_mapping_cache: Optional[Dict[int, int]] = None
    _words_cache: Optional[List[Tuple[int, int]]] = None

    class Meta:
        ordering = ["number"]
        unique_together = ("book", "number")

    def __str__(self) -> str:
        return f"Page {self.number} of {self.book.title}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override the save method to clear cache of word indices."""
        self._words_cache = None
        self._word_sentence_mapping_cache = None
        super().save(*args, **kwargs)

    def _encode_word_indices(self, word_indices: List[Tuple[int, int]]) -> str:
        """Encode word indices nested list to a compact flat list.

        [[0, 4], [5, 7], [8, 9], [10, 14], [15, 19]] -> "[0, 4, 5, 7, 8, 9, 10, 14, 15, 19]"
        """
        flattened = [index for pair in word_indices for index in pair]
        return json.dumps(flattened)

    def _decode_word_indices(self) -> List[Tuple[int, int]]:
        """Decode word indices from the flat list to nested list."""
        if not self.word_indices:
            return []
        try:
            flat_indices = json.loads(self.word_indices)
            if len(flat_indices) % 2 != 0:
                raise ValueError("Word indices DB field has an odd number of elements.")
            return list(zip(flat_indices[::2], flat_indices[1::2]))
        except json.JSONDecodeError:
            print(f"Failed to decode word_indices: {self.word_indices}")
            return []

    @property
    def words(self) -> List[Tuple[int, int]]:
        """Property to parse words from the content or retrieve from DB."""
        if self._words_cache is None or self.word_indices is None:
            if self.word_indices is None:
                self._parse_and_save_words()
            self._words_cache = self._decode_word_indices()
        return self._words_cache

    def _parse_and_save_words(self) -> None:
        """Parse words from content and save to DB."""
        parsed_words, _ = parse_words(self.content)
        self.word_indices = self._encode_word_indices(parsed_words)
        self.save(update_fields=["word_indices"])

    def extract_words(
        self, start_word_id: int, end_word_id: int
    ) -> Tuple[str, List[Tuple[int, int]]]:
        """Extract a fragment of text from start_word_id to end_word_id (inclusive).

        Returns (text_fragment, word_indices adjusted to the fragment).
        """
        words = self.words
        if not words:
            return "", []

        start_word_id = max(start_word_id, 0)
        end_word_id = min(end_word_id, len(words) - 1)
        if start_word_id > end_word_id:
            raise ValueError("Invalid word IDs")

        start_pos = words[start_word_id][0]
        end_pos = words[end_word_id][1]

        text_fragment = self.content[start_pos:end_pos]
        # todo: clear from the text html tags and add to the result map {position: tag}
        word_indices = words[start_word_id : end_word_id + 1]

        # Adjust word indices to be relative to the start of the fragment
        adjusted_indices = [(start - start_pos, end - start_pos) for start, end in word_indices]

        return text_fragment, adjusted_indices

    @property
    def word_sentence_mapping(self) -> Dict[int, int]:
        """Property to parse word to sentence mapping from DB or cache."""
        if self._word_sentence_mapping_cache is None:
            if self.word_to_sentence_map is None:
                self._detect_and_store_sentences()
            assert self.word_to_sentence_map is not None  # mypy
            # Ensure all keys are integers
            self._word_sentence_mapping_cache = {
                int(k): v for k, v in json.loads(self.word_to_sentence_map).items()
            }
        return self._word_sentence_mapping_cache

    def _detect_and_store_sentences(self) -> None:
        _, word_to_sentence = break_into_sentences(
            self.content, self.words, lang_code=self.book.language.google_code
        )
        # Ensure all keys are strings before JSON serialization
        self.word_to_sentence_map = json.dumps({str(k): v for k, v in word_to_sentence.items()})
        self.save(update_fields=["word_to_sentence_map"])
        # Ensure all keys are integers in the cache
        self._word_sentence_mapping_cache = {int(k): v for k, v in word_to_sentence.items()}


class LexicalArticle(models.Model):  # type: ignore
    """A lexical article."""

    reader_profile = models.ForeignKey(
        "LanguagePreferences", on_delete=models.CASCADE, related_name="lexical_articles"
    )
    type = models.CharField(max_length=20, choices=ARTICLE_TYPES)
    title = models.CharField(max_length=100)
    parameters = models.JSONField(default=dict)

    class Meta:
        unique_together = ("reader_profile", "title")

    def clean(self) -> None:
        if self.type == "Site":
            if "url" not in self.parameters or "window" not in self.parameters:
                raise ValidationError("Site article must have 'url' and 'window' parameters.")
        elif self.type == "Dictionary":
            if "dictionary" not in self.parameters:
                raise ValidationError("Dictionary article must have 'dictionary' parameter.")
        elif self.type not in ["Dictionary", "Site"]:
            if "model" not in self.parameters:
                raise ValidationError(f"{self.type} article must have 'model' parameter.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.clean()
        super().save(*args, **kwargs)


class LanguagePreferences(models.Model):  # type: ignore
    """Language Preferences.

    Like target language to translate this language to,
    inline translation dictionary, Lexical Sidebar Config.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="language_preferences"
    )
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name="language_preferences"
    )
    current_book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_readers",
    )
    user_language = models.ForeignKey(
        Language, on_delete=models.SET_NULL, null=True, related_name="profile_user_language"
    )
    inline_translation_type = models.CharField(max_length=20, choices=ARTICLE_TYPES)
    inline_translation_parameters = models.JSONField(default=dict)

    class Meta:
        unique_together = ("user", "language")

    @classmethod
    @transaction.atomic  # type: ignore
    def get_or_create_language_preferences(
        cls, user: CustomUser, language: Language
    ) -> "LanguagePreferences":
        """Get or create a Language Preferences for the given user and language."""
        default = user.default_language_preferences
        profile, created = cls.objects.get_or_create(
            user=user,
            language=language,
            defaults={
                "user_language": default.user_language
                if user.default_language_preferences
                else None,
                "inline_translation_type": default.inline_translation_type
                if user.default_language_preferences
                else "",
                "inline_translation_parameters": default.inline_translation_parameters
                if user.default_language_preferences
                else {},
            },
        )

        if created:
            # Copy lexical articles from the default profile
            if user.default_language_preferences:
                for article in user.default_language_preferences.lexical_articles.all():
                    LexicalArticle.objects.create(
                        reader_profile=profile,
                        type=article.type,
                        title=article.title,
                        parameters=article.parameters,
                    )

            # Set this new profile as the default
            user.default_language_preferences = profile
            user.save()

        return profile  # type: ignore

    @property
    def inline_translation(self) -> Dict[str, Any]:
        """Return inline translation as an object."""
        try:
            return {
                "type": self.inline_translation_type,
                "parameters": json.loads(self.inline_translation_parameters),
            }
        except TypeError:
            return {"type": self.inline_translation_type, "parameters": {}}

    def get_lexical_articles(self) -> list[LexicalArticle]:
        """Return all lexical articles for this reader profile."""
        return self.lexical_articles.all()  # type: ignore


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
