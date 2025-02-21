"""Sentence extraction utilities for the LexiFlux language module."""

from enum import Enum
from typing import Optional

import spacy
import spacy.language
from spacy.tokens import Doc

from lexiflux.language.nltk_tokenizer import get_punkt_tokenizer


class SentenceTokenizer(Enum):
    """Enum to select the sentence tokenizer."""

    NLTK = "nltk"
    SPACY = "spacy"


def get_spacy_sentencizer(lang_code: str) -> spacy.language.Language:
    """Get a Spacy pipeline with just the sentencizer component."""
    nlp = spacy.blank(lang_code)
    nlp.add_pipe("sentencizer")
    return nlp


def break_into_sentences(
    plain_text: str,
    word_slices: list[tuple[int, int]],
    term_word_ids: Optional[list[int]] = None,  # noqa: ARG001
    lang_code: str = "en",
    tokenizer: SentenceTokenizer = SentenceTokenizer.SPACY,
) -> tuple[list[str], dict[int, int]]:
    """Break plain text into sentences and map word IDs to sentence indices.

    Args:
    plain_text: The input text without HTML tags.
    word_slices: List of word start and end indices.
    term_word_ids: list of the highlighted word IDs, expected to be contiguous
        just for signature compatibility with the LLM version.
    tokenizer: Enum to select the tokenizer.
    lang_code: Language code for the text (e.g., 'en' for English, 'fr' for French).

    Returns:
    tuple[list[str], dict[int, int]]: A tuple containing:
        - List of sentences
        - Dictionary mapping word index to sentence index

    """
    # todo: in the sentence words is not included the punctuation
    #  that could be at the beginning and / or end of the sentence.
    #  so if we collect only the words that wont be full sentence - we may miss the punctuation
    #  maybe instead of sentence texts we better return the sentences positions
    if tokenizer == SentenceTokenizer.NLTK:
        punkt_tokenizer = get_punkt_tokenizer(lang_code)
        sentence_spans = list(punkt_tokenizer.span_tokenize(plain_text))
    elif tokenizer == SentenceTokenizer.SPACY:
        nlp = get_spacy_sentencizer(lang_code)
        doc: Doc = nlp(plain_text)
        sentence_spans = [(sent.start_char, sent.end_char) for sent in doc.sents]
    else:
        raise ValueError(f"Unsupported tokenizer: {tokenizer}")

    word_to_sentence = {}
    current_sentence = 0

    for i, (word_start, _) in enumerate(word_slices):
        while (
            current_sentence < len(sentence_spans)
            and word_start >= sentence_spans[current_sentence][1]
        ):
            current_sentence += 1

        if current_sentence < len(sentence_spans):
            word_to_sentence[i] = current_sentence
        else:
            # If we've gone past the last sentence, assign to the last sentence
            word_to_sentence[i] = len(sentence_spans) - 1

    # Create the list of sentence strings
    sentences = [plain_text[start:end] for start, end in sentence_spans]

    return sentences, word_to_sentence
