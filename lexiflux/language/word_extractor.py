"""Extract words and HTML tags from HTML content."""

import re
from enum import Enum
from typing import List, Tuple
import logging
import nltk
from lexiflux.language.nltk_tokenizer import ensure_nltk_data


from lexiflux.language.html_tags_cleaner import parse_tags

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WordTokenizer(Enum):
    """Enum to select the word tokenizer."""

    NLTK = "nltk"  # todo: NLTK can skip whole paragraphs without tokenizing them
    NAIVE = "naive"


def naive_word_tokenize(text: str) -> List[str]:
    """A word tokenizer that splits on whitespace and punctuation."""
    return re.findall(r"\b\w+\b", text)


def is_punctuation(token: str) -> bool:
    """Check if a token is a punctuation mark."""
    return all(not c.isalnum() for c in token)


def parse_words(
    content: str, lang_code: str = "en", tokenizer: WordTokenizer = WordTokenizer.NAIVE
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """Extract words and HTML tags from HTML content."""

    cleaned_content, tag_positions, escaped_chars = parse_tags(content)
    logger.debug(f"Cleaned content: {cleaned_content}")
    logger.debug(f"Tag positions: {[content[start:end] for start, end in tag_positions]}")
    logger.debug(f"Escaped characters: {[content[start:end] for start, end, _ in escaped_chars]}")

    if tokenizer == WordTokenizer.NLTK:
        ensure_nltk_data(f"tokenizers/punkt/{lang_code}.pickle", "punkt")
        try:
            words = nltk.tokenize.word_tokenize(
                cleaned_content, language=lang_code, preserve_line=True
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
    logger.debug(
        "Words found: "
        f"{[cleaned_content[start:end] for start, end in word_slices_cleaned_content]}"
    )

    # Recalculate word positions for the original content
    original_word_positions = recalculate_positions(
        word_slices_cleaned_content, tag_positions, escaped_chars, content
    )

    return original_word_positions, tag_positions


def recalculate_positions(  # pylint: disable=too-many-locals
    word_positions: List[Tuple[int, int]],
    tag_positions: List[Tuple[int, int]],
    escaped_chars: List[Tuple[int, int, str]],
    content: str,  # just for debugging
) -> List[Tuple[int, int]]:
    """Recalculate word positions for the original content."""
    original_word_positions = []
    tag_index = 0
    escaped_char_index = 0
    offset = 0

    for start, end in word_positions:
        # Adjust for tags before the word
        while tag_index < len(tag_positions) and tag_positions[tag_index][0] <= start + offset:
            offset += tag_positions[tag_index][1] - tag_positions[tag_index][0]
            tag_index += 1
        logger.debug(f"Word: {start}, {end}, Offset: {offset}, Tag index: {tag_index}")

        # Adjust for escaped characters affecting word boundaries
        new_start = start + offset
        new_end = end + offset

        # Adjust for escaped characters before and within the word
        while (
            escaped_char_index < len(escaped_chars)
            and escaped_chars[escaped_char_index][0] < new_end
        ):
            escaped_start, escaped_end, unescaped = escaped_chars[escaped_char_index]
            if new_start <= escaped_start < new_end:
                logger.debug(
                    f"Escaped character is within the word {unescaped}: "
                    f"new start: {new_start}, new end: {new_end}, "
                    f"escaped start: {escaped_start}, escaped end: {escaped_end}"
                )
                new_end += (escaped_end - escaped_start) - len(unescaped)
                logger.debug(f"new_end: {new_end}")
            elif escaped_start < new_start:
                logger.debug(
                    f"Escaped character affects the word start {unescaped}: "
                    f"new start: {new_start}, new end: {new_end}, "
                    f"escaped start: {escaped_start}, escaped end: {escaped_end}"
                )
                new_start += (escaped_end - escaped_start) - len(unescaped)
                new_end += (escaped_end - escaped_start) - len(unescaped)
                logger.debug(f"new_start: {new_start} new_end: {new_end}")
            escaped_char_index += 1

        # if tags inside the word we break it into the separate words with this tags
        while tag_index < len(tag_positions) and tag_positions[tag_index][0] < new_end:
            tag_start, tag_end = tag_positions[tag_index]
            new_end += tag_end - tag_start
            logger.debug(
                f"Tag inside the word: {tag_start}, {tag_end} "
                f"({content[tag_start:tag_end]}), new end: {new_end}"
            )
            if new_start < tag_start:  # non-empty word part before the tag
                original_word_positions.append((new_start, tag_start))
                logger.debug(
                    f"Add word part before tag ({content[new_start:tag_end]}), "
                    f"New start: {new_start}"
                )
            new_start = tag_end
            logger.debug(f"New start: {new_start}")
            tag_index += 1

        original_word_positions.append((new_start, new_end))
        offset = new_end - end

    return original_word_positions
