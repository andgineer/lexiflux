"""Detect language using deep_translator."""

import os
from functools import lru_cache
import logging
from deep_translator import single_detection


log = logging.getLogger()


class DeepTranslatorDetectLanguage:  # pylint: disable=too-few-public-methods
    """Detect language using deep_translator."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("DETECTLANGUAGE_API_KEY")
        if not self.api_key:
            log.warning(
                "DETECTLANGUAGE_API_KEY not set. Please get your API Key at "
                "https://detectlanguage.com/documentation and set it "
                "to env var DETECTLANGUAGE_API_KEY"
            )

    def detect(self, text: str) -> str:
        """Detect language using deep_translator."""
        log.debug("Fragment: %s", text)
        try:
            result = single_detection(text, api_key=self.api_key)
            log.debug("Detected language: %s", result)
            # Since single_detection doesn't provide confidence, we'll use a default value
            return result  # type: ignore
        except KeyError:
            log.error(
                "Please get your API Key at https://detectlanguage.com/documentation"
                " and set it to env var DETECTLANGUAGE_API_KEY"
            )
            return "en"
        except Exception as exc:  # pylint: disable=broad-except
            log.error("Failed to detect language: %s", exc)
            return "en"


@lru_cache(maxsize=1)
def language_detector() -> DeepTranslatorDetectLanguage:
    """Singleton for DeepTranslatorDetectLanguage."""
    return DeepTranslatorDetectLanguage()


if __name__ == "__main__":  # pragma: no cover
    print(language_detector().detect("Dobar dan!"))
