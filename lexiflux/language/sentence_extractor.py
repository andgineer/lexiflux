"""Sentence extraction utilities for the LexiFlux language module."""

from enum import Enum
from typing import List, Tuple, Dict
import nltk
from nltk.tokenize import sent_tokenize


nltk.download("punkt", quiet=True)


class SentenceTokenizer(Enum):
    """Enum to select the sentence tokenizer."""

    NLTK = "nltk"


def break_into_sentences(
    plain_text: str,
    word_slices: List[Tuple[int, int]],
    term_word_ids: List[int],  # pylint: disable=unused-argument
    lang_code: str = "en",
    tokenizer: SentenceTokenizer = SentenceTokenizer.NLTK,
) -> Tuple[List[str], Dict[int, int]]:
    """
    Break plain text into sentences and map word IDs to sentence indices.

    Args:
    plain_text: The input text without HTML tags.
    word_slices: List of word start and end indices.
    term_word_ids: list of the highlighted word IDs, expected to be contiguous
        just for signature compatibility with the LLM version.
    tokenizer: Enum to select the tokenizer.
    lang_code: Language code for the text (e.g., 'en' for English, 'fr' for French).

    Returns:
    Tuple[List[str], Dict[int, int]]: A tuple containing:
        - List of sentences
        - Dictionary mapping word index to sentence index
    """
    # todo: in the sentence words is not included the punctuation
    #  that could be at the beginning and / or end of the sentence.
    #  maybe instead of sentence textx we better return the sentences positions
    if tokenizer == SentenceTokenizer.NLTK:
        try:
            nltk.data.find(f"tokenizers/punkt/{lang_code}.pickle")
            sentences = sent_tokenize(plain_text, language=lang_code)
        except LookupError:
            print(f"NLTK punkt tokenizer not available for {lang_code}. Using default.")
            sentences = sent_tokenize(plain_text)
    else:
        raise ValueError(f"Unsupported tokenizer: {tokenizer}")

    word_to_sentence = {}
    current_sentence = 0
    sentence_end = 0

    for i, (word_start, _) in enumerate(word_slices):
        while current_sentence < len(sentences) and word_start >= sentence_end:
            sentence_end += len(sentences[current_sentence])
            current_sentence += 1

        word_to_sentence[i] = current_sentence - 1

    return sentences, word_to_sentence
