"""Models for the lexiflux app."""

import re
from html import unescape
from typing import TypeAlias, Tuple, List, Any, Dict, Optional

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from transliterate import get_available_language_codes, translit
from unidecode import unidecode

from lexiflux.language.sentence_extractor import break_into_sentences
from lexiflux.language.word_extractor import parse_words
from lexiflux.language_preferences_default import create_default_language_preferences

BOOK_CODE_LENGTH = 100
SUPPORTED_CHAT_MODELS = {
    "ChatOpenAI": ["api_key", "temperature"],
    "ChatMistralAI": ["api_key", "temperature"],
    "ChatAnthropic": ["api_key", "temperature"],
    "Ollama": ["temperature"],
}

TocEntry: TypeAlias = Tuple[str, int, int]  # <title>, <page num>, <word on the page num>
Toc: TypeAlias = List[TocEntry]


class LexicalArticleType(models.TextChoices):  # type: ignore  # pylint: disable=too-many-ancestors
    """Types of lexical articles."""

    # todo: extract from Llm.article_names()
    TRANSLATE = "Translate", _("Translate")
    SENTENCE = "Sentence", _("Sentence")
    EXPLAIN = "Explain", _("Explain")
    LEXICAL = "Lexical", _("Lexical")
    AI = "AI", _("AI")
    DICTIONARY = "Dictionary", _("Dictionary")
    SITE = "Site", _("Site")


LEXICAL_ARTICLE_PARAMETERS = {
    "Translate": ["model"],
    "Sentence": ["model"],
    "Explain": ["model"],
    "Examples": ["model"],
    "Lexical": ["model"],
    "Dictionary": ["dictionary"],
    "Site": ["url", "window"],
    "AI": ["model", "prompt"],
}


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
    stop_words = {"the", "et", "i", "a", "an", "and", "or", "of", "in", "on", "at", "to"}
    pattern = re.compile(r"\b[^\s]+\b")
    return [
        word.lower()
        for word in pattern.findall(text)
        if word.lower() not in stop_words and len(word) > 1
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

    @classmethod
    def find(
        cls: Any,
        name: Optional[str] = None,
        google_code: Optional[str] = None,
        epub_code: Optional[str] = None,
    ) -> Optional[str]:
        """Find language by provided parameters (which are not None).

        Return language name if found, None otherwise.
        """
        query = Q()
        if name:
            query |= Q(name=name)
        if google_code:
            query |= Q(google_code=google_code)
        if epub_code:
            query |= Q(epub_code=epub_code)

        language = cls.objects.filter(query).first()
        return language.name if language else None


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
    toc = models.JSONField(default=list, blank=True)
    anchor_map = models.JSONField(
        default=dict, blank=True, help_text="Maps anchors to page numbers and EPUB items"
    )

    @property
    def current_reading_by_count(self) -> int:
        """Return the number of users currently reading this book."""
        return self.current_readers.count()  # type: ignore

    def generate_unique_book_code(self) -> str:
        """Generate a unique book code."""

        def transliterate(book_code: str, lang_code: Optional[str]) -> str:
            try:
                if lang_code in get_available_language_codes():
                    book_code = translit(book_code, lang_code, reversed=True)
                book_code = unidecode(book_code)
                # replace all non-word characters with a dash
                book_code = re.sub(r"[^a-zA-Z0-9-]+", "", book_code).lower()
                if book_code.replace("-", "").strip() == "":
                    return "book"
                return book_code
            except Exception:  # pylint: disable=broad-except
                return unidecode(book_code)

        title_words = split_into_words(self.title)
        author_words = split_into_words(self.author.name)
        code = "-".join(title_words[:2]) if title_words else "book"
        if author_words:
            code = f"{code}-{author_words[-1]}"

        # Transliterate the code to latin chars if the language is supported
        code = transliterate(code, self.language.google_code)

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

        # Ensure anchor_map is a dictionary
        if not isinstance(self.anchor_map, dict):
            self.anchor_map = {}

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
    word_slices = models.JSONField(
        null=True, blank=True, help_text="List of tuples with start and end index for each word."
    )
    word_to_sentence_map = models.JSONField(null=True, blank=True)

    _word_sentence_mapping_cache: Optional[Dict[int, int]] = None
    _words_cache: Optional[List[Tuple[int, int]]] = None

    class Meta:
        ordering = ["number"]
        unique_together = ("book", "number")

    def __str__(self) -> str:
        return f"Page {self.number} of {self.book.title}"

    def clean(self) -> None:
        super().clean()
        if self.word_slices is not None:
            if not isinstance(self.word_slices, list):
                raise ValidationError({"word_slices": "Must be a list of tuples"})
            # todo: fail in tests
            # for item in self.word_slices:
            #     if not (isinstance(item, list) and len(item) == 2
            #     and all(isinstance(x, int) for x in item)):
            #         raise ValidationError(
            #         {"word_slices": "Each item must be a tuple of two integers"}
            #         )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override the save method to clear cache of word indices."""
        self._words_cache = None
        self._word_sentence_mapping_cache = None
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def words(self) -> List[Tuple[int, int]]:
        """Property to parse words from the content or retrieve from DB."""
        if self._words_cache is None:
            if self.word_slices is None:
                self._parse_and_save_words()
            else:
                self._words_cache = self.word_slices
        return self._words_cache  # type: ignore

    def word_string(self, word_id: int) -> str:
        """Get an unescaped word string by its ID."""
        if 0 <= word_id < len(self.words):
            start, end = self.words[word_id]
            return unescape(self.content[start:end])  # type: ignore
        raise ValueError(f"Invalid word ID: {word_id}")

    def _parse_and_save_words(self) -> None:
        """Parse words from content and save to DB."""
        parsed_words, _ = parse_words(self.content, lang_code=self.book.language.google_code)
        self.word_slices = parsed_words
        self.save(update_fields=["word_slices"])
        self._words_cache = parsed_words

    def extract_words(
        self, start_word_id: int, end_word_id: int
    ) -> Tuple[str, List[Tuple[int, int]]]:
        """Extract a fragment of text from start_word_id to end_word_id (inclusive)."""
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
        word_slices = words[start_word_id : end_word_id + 1]

        # Adjust word indices to be relative to the start of the fragment
        adjusted_indices = [(start - start_pos, end - start_pos) for start, end in word_slices]

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
                int(k): v for k, v in self.word_to_sentence_map.items()
            }
        return self._word_sentence_mapping_cache

    def _detect_and_store_sentences(self) -> None:
        _, word_to_sentence = break_into_sentences(
            self.content, self.words, lang_code=self.book.language.google_code
        )
        # Ensure all keys are strings
        self.word_to_sentence_map = {str(k): v for k, v in word_to_sentence.items()}
        self.save(update_fields=["word_to_sentence_map"])
        # Ensure all keys are integers in the cache
        self._word_sentence_mapping_cache = {int(k): v for k, v in word_to_sentence.items()}


class BookImage(models.Model):  # type: ignore
    """Model to store book images as blobs."""

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="images")
    image_data = models.BinaryField()
    content_type = models.CharField(max_length=100)
    filename = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f"Image {self.filename} for {self.book.title}"


class AIModelConfig(models.Model):  # type: ignore
    """Model to store settings for AI models used in the application."""

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="ai_model_settings"
    )
    chat_model = models.CharField(max_length=100, help_text="LangChain Chat model class")
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="AI model settings.",
    )

    class Meta:
        unique_together = ("user", "chat_model")

    @classmethod
    def get_or_create_ai_model_config(cls, user: CustomUser, chat_model: str) -> "AIModelConfig":
        """Get or create AI model config for the given user and chat model."""
        supported_settings = SUPPORTED_CHAT_MODELS.get(chat_model, [])
        config, created = AIModelConfig.objects.get_or_create(
            user=user,
            chat_model=chat_model,
            defaults={"settings": {setting: "" for setting in supported_settings}},
        )
        if created:
            config.save()
        return config  # type: ignore

    def clean(self) -> None:
        super().clean()
        errors = {}
        for key, value in self.settings.items():
            if key == "temperature" and value:
                try:
                    float_value = float(value)
                    if not 0 <= float_value <= 1:
                        errors[key] = f"Temperature must be between 0 and 1, got {float_value}"
                except ValueError:
                    errors[key] = f"Temperature must be a number, got {value}"

        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.user.username} - {self.chat_model} Settings"


class LexicalArticle(models.Model):  # type: ignore
    """A lexical article."""

    language_preferences = models.ForeignKey(
        "LanguagePreferences", on_delete=models.CASCADE, related_name="lexical_articles"
    )
    type = models.CharField(
        max_length=20,
        choices=LexicalArticleType.choices,
    )
    title = models.CharField(max_length=100)
    parameters = models.JSONField(default=dict)
    order = models.IntegerField(default=0)

    class Meta:
        unique_together = ("language_preferences", "title")
        ordering = ["order"]

    def clean(self) -> None:
        if self.type == "Site":
            if "url" not in self.parameters or "window" not in self.parameters:
                raise ValidationError("Site article must have 'url' and 'window' parameters.")
        elif self.type == "Dictionary":
            if "dictionary" not in self.parameters:
                raise ValidationError("Dictionary article must have 'dictionary' parameter.")
        elif self.type == "AI":
            if "prompt" not in self.parameters:
                raise ValidationError("AI article must have 'prompt' parameter.")
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
        Language,
        on_delete=models.SET_NULL,
        null=True,
        related_name="language_preferences_user_language",
    )
    inline_translation_type = models.CharField(
        max_length=20, choices=LexicalArticleType.choices, default=LexicalArticleType.TRANSLATE
    )
    inline_translation_parameters = models.JSONField(default=dict)

    class Meta:
        unique_together = ("user", "language")

    def clean(self) -> None:
        super().clean()
        if self.inline_translation_type not in LexicalArticleType.values:
            raise ValidationError(
                {
                    "inline_translation_type": _(
                        "'%(value)s' is not a valid choice. Valid choices are %(choices)s."
                    )
                    % {
                        "value": self.inline_translation_type,
                        "choices": ", ".join(LexicalArticleType.values),
                    }
                }
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    @transaction.atomic  # type: ignore
    def get_or_create_language_preferences(
        cls, user: CustomUser, language: Language
    ) -> "LanguagePreferences":
        """Get or create a Language Preferences for the given user and language."""
        default = user.default_language_preferences
        if default is None:
            # Use the first existing record or create a new default
            default = cls.objects.filter(user=user).first() or create_default_language_preferences(
                user
            )
            user.default_language_preferences = default
            user.save()

        preferences, created = cls.objects.get_or_create(
            user=user,
            language=language,
            defaults={
                "user_language": default.user_language,
                "inline_translation_type": default.inline_translation_type,
                "inline_translation_parameters": default.inline_translation_parameters,
            },
        )

        if created:
            # Copy lexical articles from the default language preferences
            for article in default.lexical_articles.all():
                LexicalArticle.objects.create(
                    language_preferences=preferences,
                    type=article.type,
                    title=article.title,
                    parameters=article.parameters,
                )

        return preferences  # type: ignore

    @property
    def inline_translation(self) -> Dict[str, Any]:
        """Return inline translation configuration."""
        return {
            "type": self.inline_translation_type,
            "parameters": self.inline_translation_parameters,
        }

    def get_lexical_articles(self) -> list[LexicalArticle]:
        """Return all lexical articles for this language_preferences."""
        return self.lexical_articles.all().order_by("order")  # type: ignore


class ReadingLoc(models.Model):  # type: ignore  # pylint: disable=too-many-instance-attributes
    """A reading location.

    Current reading location and jump history.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reading_pos"
    )
    book = models.ForeignKey("Book", on_delete=models.CASCADE)
    jump_history = models.JSONField(default=list)
    current_jump = models.IntegerField(default=-1)
    page_number = models.PositiveIntegerField(help_text="Page number currently being read")
    word = models.PositiveIntegerField(help_text="Last word read on the current reading page")
    last_access = models.DateTimeField(default=timezone.now)
    furthest_reading_page = models.PositiveIntegerField(
        default=0,
        help_text="Stores the furthest reading page number",
    )
    furthest_reading_word = models.PositiveIntegerField(
        default=0,
        help_text="Stores the furthest reading top word on the furthest page",
    )
    last_position_percent = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("user", "book")

    def jump(self, page_number: int, word: int) -> None:
        """Jump to a new reading location."""
        print("Jumping to", page_number, word)
        self.jump_history = self.jump_history[: self.current_jump + 1]
        self.jump_history.append({"page_number": page_number, "word": word})
        self.current_jump = len(self.jump_history) - 1
        self._update_reading_location(page_number, word)
        self.save()

    def jump_back(self) -> Tuple[int, int]:
        """Jump back to the previous reading location."""
        if self.current_jump > 0:
            self.current_jump -= 1
            position = self.jump_history[self.current_jump]
            self._update_reading_location(position["page_number"], position["word"])
            self.save()
            return self.page_number, self.word
        return self.page_number, self.word

    def jump_forward(self) -> Tuple[int, int]:
        """Jump forward to the next reading location."""
        if self.current_jump < len(self.jump_history) - 1:
            self.current_jump += 1
            position = self.jump_history[self.current_jump]
            self._update_reading_location(position["page_number"], position["word"])
            self.save()
            return self.page_number, self.word
        return self.page_number, self.word

    def _update_reading_location(self, page_number: int, word: int) -> None:
        """Update the current reading location.

        To use inside jump* methods.
        Do not call save() and no need to update the jump_history.
        """
        self.page_number = page_number
        self.word = word
        self.last_access = timezone.now()

        # Check and update the furthest reading point
        if page_number > self.furthest_reading_page or (
            page_number == self.furthest_reading_page and word > self.furthest_reading_word
        ):
            self.furthest_reading_page = page_number
            self.furthest_reading_word = word

        total_pages = self.book.pages.count()
        self.last_position_percent = (
            (page_number - 1) / (total_pages - 1) if total_pages > 1 else 0.0
        )

    @classmethod
    def update_reading_location(
        cls, user: CustomUser, book_id: int, page_number: int, top_word_id: int
    ) -> None:
        """Update the current reading location."""
        loc, _ = cls.objects.get_or_create(
            user=user, book_id=book_id, defaults={"page_number": page_number, "word": top_word_id}
        )
        loc._update_reading_location(page_number, top_word_id)  # pylint: disable=protected-access

        # Update the current jump in jump_history
        if loc.jump_history and loc.current_jump >= 0:
            loc.jump_history[loc.current_jump] = {"page_number": page_number, "word": top_word_id}

        loc.save()

    @classmethod
    def get_or_create_reading_loc(cls, user: CustomUser, book: Book) -> "ReadingLoc":
        """Get or create a reading location."""
        loc, _ = cls.objects.get_or_create(
            user=user, book=book, defaults={"page_number": 1, "word": 0}
        )
        return loc  # type: ignore
