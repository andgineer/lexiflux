"""Book base class for importing books from different formats."""
import logging
from typing import Any, Dict, Optional
from collections import Counter
from lexiflux.language.translation import detect_language, find_language


log = logging.getLogger()


class MetadataField:  # pylint: disable=too-few-public-methods
    """Book metadata fields."""

    TITLE = "title"
    AUTHOR = "author"
    RELEASED = "released"
    LANGUAGE = "language"
    CREDITS = "credits"


class BookBase:
    """Base class for importing books from different formats."""

    meta: Dict[str, Any]

    @staticmethod
    def get_language_group(lang: str) -> str:
        """Define language similarity groups."""
        lang_groups = {"group:bs-hr-sr": {"bs", "hr", "sr"}}
        return next(
            (group_name for group_name, group_langs in lang_groups.items() if lang in group_langs),
            lang,
        )

    def get_random_words(self, words_num: int = 15) -> str:
        """Get random words from the book."""
        raise NotImplementedError

    def detect_language(self) -> Optional[str]:
        """Detect language of the book extracting random fragments of the text.

        Returns lang code.
        """
        languages = [detect_language(self.get_random_words()) for _ in range(3)]

        # If no clear majority, try additional random fragments
        attempts = 0
        while attempts < 10:
            lang_counter = Counter(map(self.get_language_group, languages))
            most_common_lang, most_common_count = lang_counter.most_common(1)[0]

            # Check if the most common language group count is more than the sum of other counts
            if most_common_count > sum(
                count for lang, count in lang_counter.items() if lang != most_common_lang
            ):
                break

            random_fragment = self.get_random_words()
            languages.append(detect_language(random_fragment))
            attempts += 1

        # Count languages considering similarity groups
        lang_counter = Counter(map(self.get_language_group, languages))

        # Find the most common language group
        most_common_lang, _ = lang_counter.most_common(1)[0]

        # If the group consists of similar languages, find the most common individual language
        if most_common_lang.startswith("group:"):  # found lang group, should select just one lang
            result = Counter(
                [lang for lang in languages if self.get_language_group(lang) == most_common_lang]
            ).most_common(1)[0][0]
        else:
            result = most_common_lang

        if language_name := find_language(name=result, google_code=result, epub_code=result):
            return language_name  # type: ignore
        return None

    def get_language(self) -> str:
        """Get language from meta or detect from the book text."""
        if language_value := self.meta.get(MetadataField.LANGUAGE):
            if language_name := find_language(
                name=language_value, google_code=language_value, epub_code=language_value
            ):
                # Update the language to its name in case it was found by code
                log.debug("Language '%s' found in meta.", language_name)
                return language_name  # type: ignore
        # Detect language if not found in meta
        language_name = self.detect_language()
        log.debug("Language '%s' detected.", language_name)
        return language_name  # type: ignore
