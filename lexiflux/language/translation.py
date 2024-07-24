"""Translation module."""

import logging
from functools import lru_cache
from typing import List, Dict, Tuple

from deep_translator import (
    GoogleTranslator,
    MyMemoryTranslator,
    LingueeTranslator,
    PonsTranslator,
)

log = logging.getLogger()

AVAILABLE_TRANSLATORS: Dict[str, Tuple[type, str]] = {
    "GoogleTranslator": (GoogleTranslator, "Google Translator"),
    "MyMemoryTranslator": (MyMemoryTranslator, "MyMemory Translator"),
    "LingueeTranslator": (LingueeTranslator, "Linguee Translator"),
    "PonsTranslator": (PonsTranslator, "PONS Translator"),
}


class Translator:
    """Translator."""

    def __init__(
        self, translator_name: str, source_language_code: str, target_language_code: str
    ) -> None:
        """Initialize Translator."""
        if translator_name not in AVAILABLE_TRANSLATORS:
            raise ValueError(f"Unsupported translator: {translator_name}")

        translator_class, _ = AVAILABLE_TRANSLATORS[translator_name]
        self._translator = translator_class(
            source=source_language_code, target=target_language_code
        )
        log.debug(
            "Translator: %s, source: %s, target %s",
            self._translator,
            source_language_code,
            target_language_code,
        )

    @lru_cache(maxsize=128)
    def translate(self, text: str) -> str:
        """Translate text."""
        return self._translator.translate(text)  # type: ignore

    @classmethod
    def available_translators(cls) -> List[Dict[str, str]]:
        """Return list of available translator names and labels."""
        return [
            {"value": name, "label": label} for name, (_, label) in AVAILABLE_TRANSLATORS.items()
        ]


@lru_cache(maxsize=128)
def get_translator(
    translator_name: str, source_language_code: str, target_language_code: str
) -> Translator:
    """Get translator."""
    return Translator(translator_name, source_language_code, target_language_code)
