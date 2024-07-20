"""Extract words and HTML tags from HTML content."""

from enum import Enum
from typing import List, Tuple
import logging
import nltk


from lexiflux.language.html_tags_cleaner import parse_tags

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    nltk.download("punkt", quiet=True)
except FileExistsError:
    pass


class WordTokenizer(Enum):
    """Enum to select the word tokenizer."""

    NLTK = "nltk"


def is_punctuation(token: str) -> bool:
    """Check if a token is a punctuation mark."""
    return all(not c.isalnum() for c in token)


def parse_words(
    content: str, lang_code: str = "en", tokenizer: WordTokenizer = WordTokenizer.NLTK
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """Extract words and HTML tags from HTML content."""

    cleaned_content, tag_positions = parse_tags(content)
    logger.info(f"Cleaned content: {cleaned_content}")
    logger.info(f"Tag positions: {tag_positions}")

    if tokenizer == WordTokenizer.NLTK:
        try:
            nltk.data.find(f"tokenizers/punkt/{lang_code}.pickle")
            words = nltk.tokenize.word_tokenize(
                cleaned_content, language=lang_code, preserve_line=True
            )
        except LookupError:
            logger.warning(f"NLTK word tokenizer not available for {lang_code}. Using default.")
            words = nltk.tokenize.word_tokenize(cleaned_content, preserve_line=True)
    else:
        raise ValueError(f"Unsupported tokenizer: {tokenizer}")

    # Calculate word positions in the cleaned content
    word_positions = []
    current_position = 0
    for word in words:
        if not is_punctuation(word):
            start = cleaned_content.find(word, current_position)
            if start != -1:
                end = start + len(word)
                word_positions.append((start, end))
                current_position = end
        else:
            current_position = cleaned_content.find(word, current_position) + len(word)

    # Recalculate word positions for the original content
    original_word_positions = recalculate_positions(word_positions, tag_positions)

    return original_word_positions, tag_positions


def recalculate_positions(
    word_positions: List[Tuple[int, int]], tag_positions: List[Tuple[int, int]]
) -> List[Tuple[int, int]]:
    """Recalculate word positions for the original content."""
    original_word_positions = []
    tag_index = 0
    tag_offset = 0

    for start, end in word_positions:
        # Adjust for tags before the word
        while tag_index < len(tag_positions) and tag_positions[tag_index][0] <= start + tag_offset:
            tag_offset += tag_positions[tag_index][1] - tag_positions[tag_index][0]
            tag_index += 1

        # Calculate new start and end positions
        new_start = start + tag_offset
        new_end = end + tag_offset

        original_word_positions.append((new_start, new_end))

    return original_word_positions
