"""Extract words and HTML tags from HTML content."""

import logging
import re
from enum import Enum

import nltk

from lexiflux.language.nltk_tokenizer import ensure_nltk_data
from lexiflux.language.parse_html_text_content import parse_html_content

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WordTokenizer(Enum):
    """Enum to select the word tokenizer."""

    NLTK = "nltk"  # todo: NLTK can skip whole paragraphs without tokenizing them
    NAIVE = "naive"


def naive_word_tokenize(text: str) -> list[str]:
    """A word tokenizer that splits on whitespace and punctuation."""
    return re.findall(r"\b\w+\b", text)


def is_punctuation(token: str) -> bool:
    """Check if a token is a punctuation mark."""
    return all(not c.isalnum() for c in token)


def parse_words(
    content: str,
    lang_code: str = "en",
    tokenizer: WordTokenizer = WordTokenizer.NAIVE,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Extract words and HTML tags from HTML content."""
    cleaned_content, tag_positions, escaped_chars = parse_html_content(content)

    if tokenizer == WordTokenizer.NLTK:
        ensure_nltk_data(f"tokenizers/punkt/{lang_code}.pickle", "punkt")
        try:
            words = nltk.tokenize.word_tokenize(
                cleaned_content,
                language=lang_code,
                preserve_line=True,
            )
        except LookupError:
            logger.warning(f"NLTK word tokenizer not available for {lang_code}. Using default.")
            words = nltk.tokenize.word_tokenize(cleaned_content, preserve_line=True)
    elif tokenizer == WordTokenizer.NAIVE:
        words = naive_word_tokenize(cleaned_content)
    else:
        raise ValueError(f"Unsupported tokenizer: {tokenizer}")

    # Calculate word positions in the cleaned content
    word_slices_cleaned_content = []
    current_position = 0
    for word in words:
        if not is_punctuation(word):
            start = cleaned_content.find(word, current_position)
            if start != -1:
                end = start + len(word)
                word_slices_cleaned_content.append((start, end))
                current_position = end
        else:
            current_position = cleaned_content.find(word, current_position) + len(word)

    # Recalculate word positions for the original content
    original_word_positions = recalculate_positions(
        word_slices_cleaned_content,
        tag_positions,
        escaped_chars,
        content,
    )

    return original_word_positions, tag_positions


def recalculate_positions(  # pylint: disable=too-many-locals
    word_positions: list[tuple[int, int]],
    tag_positions: list[tuple[int, int]],
    escaped_chars: list[tuple[int, int, str]],
    content: str,
) -> list[tuple[int, int]]:
    """Recalculate word positions for the original content."""
    original_word_positions = []
    tag_index = 0
    escaped_char_index = 0
    offset = 0

    for start, end in word_positions:
        # Adjust tags/escaped before word
        while True:
            next_tag_pos = (
                tag_positions[tag_index][0] if tag_index < len(tag_positions) else float("inf")
            )
            next_escaped_pos = (
                escaped_chars[escaped_char_index][0]
                if escaped_char_index < len(escaped_chars)
                else float("inf")
            )

            if min(next_tag_pos, next_escaped_pos) > start + offset:
                break

            if next_tag_pos <= next_escaped_pos:
                offset += tag_positions[tag_index][1] - tag_positions[tag_index][0]
                tag_index += 1
            else:
                escaped_start, escaped_end, unescaped = escaped_chars[escaped_char_index]
                offset += (escaped_end - escaped_start) - len(unescaped)
                escaped_char_index += 1

        new_start = start + offset
        new_end = end + offset
        current_position = new_start

        # Process tags and escaped chars within the word
        while current_position < new_end:
            next_tag_pos = (
                tag_positions[tag_index][0] if tag_index < len(tag_positions) else float("inf")
            )
            next_escaped_pos = (
                escaped_chars[escaped_char_index][0]
                if escaped_char_index < len(escaped_chars)
                else float("inf")
            )

            next_pos = min(next_tag_pos, next_escaped_pos, new_end)

            if next_pos == new_end:
                break
            if next_pos == next_tag_pos:
                tag_start, tag_end = tag_positions[tag_index]
                if new_start < tag_start and (
                    content[new_start:tag_start].strip()
                    and not is_punctuation(content[new_start:tag_start].strip())
                ):
                    original_word_positions.append((new_start, tag_start))
                new_start = tag_end
                current_position = tag_end
                end_offset = tag_end - tag_start
                new_end += end_offset
                offset += end_offset
                tag_index += 1

            else:  # next_pos == next_escaped_pos
                escaped_start, escaped_end, unescaped = escaped_chars[escaped_char_index]
                current_position = escaped_end
                end_offset = (escaped_end - escaped_start) - len(unescaped)
                new_end += end_offset
                offset += end_offset
                escaped_char_index += 1

        if new_start < new_end and (
            content[new_start:new_end].strip()
            and not is_punctuation(content[new_start:new_end].strip())
        ):
            original_word_positions.append((new_start, new_end))

    return original_word_positions
