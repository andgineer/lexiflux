"""Detect language using Google Translate API through googletrans package."""

import asyncio
import logging
from functools import lru_cache

from googletrans import Translator

MIN_TEXT_CHARS = 2

logger = logging.getLogger(__name__)


class InvalidInputError(Exception):
    """Raised when input text is invalid for language detection."""


class GoogleTranslateDetectLanguage:
    """Detect language using Google Translate API through googletrans package."""

    def __init__(self) -> None:
        """Initialize the translator."""
        self.translator = Translator()
        # Test connection on initialization
        try:
            asyncio.get_event_loop().run_until_complete(self.translator.detect("test"))
        except Exception as e:
            logger.error(f"Failed to initialize Google Translate connection: {e}")
            raise

    def _validate_input(self, text: str) -> None:
        """Validate input text before language detection.

        Raises:
            InvalidInputError: If text is empty or contains only whitespace

        """
        if not text or text.isspace():
            raise InvalidInputError("Input text cannot be empty or contain only whitespace")
        if len(text.strip()) < MIN_TEXT_CHARS:
            raise InvalidInputError("Input text must contain at least 2 non-whitespace characters")

    def detect(self, text: str) -> str:
        """Detect language using Google Translate.

        Returns:
            ISO 639-1 language code (2 letters) in lower case

        Raises:
            InvalidInputError: If input text is invalid
            Exception: If language detection fails

        """
        try:
            self._validate_input(text)
            # Run the async detection in an event loop
            detection = asyncio.get_event_loop().run_until_complete(
                self.translator.detect(text.replace("\n", " ")),
            )
            return detection.lang.lower()  # type: ignore
        except InvalidInputError:
            raise
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            raise

    def detect_all(self, text: str) -> tuple[list[str], list[float]]:
        """Return top 3 language predictions with confidence scores.

        Just mock the fastText detector interface - googletrans does not have such feature.

        Raises:
            InvalidInputError: If input text is invalid
            Exception: If language detection fails

        """
        try:
            self._validate_input(text)
            detection = asyncio.get_event_loop().run_until_complete(
                self.translator.detect(text.replace("\n", " ")),
            )
            return ([detection.lang], [detection.confidence])
        except InvalidInputError:
            raise
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            raise


@lru_cache(maxsize=1)
def language_detector() -> GoogleTranslateDetectLanguage:
    """Singleton for GoogleTranslateDetectLanguage."""
    return GoogleTranslateDetectLanguage()


if __name__ == "__main__":  # pragma: no cover
    print(language_detector().detect("Dobar dan!"))
