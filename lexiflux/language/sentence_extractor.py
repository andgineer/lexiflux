"""Sentence extraction utilities for the LexiFlux language module."""

from enum import Enum
from typing import List, Tuple, Dict, Optional
import spacy
from spacy.cli import download
import nltk
from nltk.tokenize import sent_tokenize


nltk.download("punkt", quiet=True)


class SentenceTokenizer(Enum):
    """Enum to select the sentence tokenizer."""

    SPACY = "spacy"
    NLTK = "nltk"


# Global cache for loaded models
loaded_models: Dict[str, spacy.language.Language] = {}

SPACY_MODELS = {
    "en": "en_core_web_sm",
    "de": "de_core_news_sm",
    "fr": "fr_core_news_sm",
    "es": "es_core_news_sm",
    # Add more languages as needed
}


def ensure_model_installed(model_name: str) -> None:
    """Ensure that the specified spaCy model is installed."""
    try:
        spacy.load(model_name)
    except OSError:
        print(f"Downloading model {model_name}...")
        download(model_name)


def get_spacy_model(lang_code: str) -> Optional[spacy.language.Language]:
    """
    Get (and if necessary, download) the appropriate spaCy model for the given language code.
    Returns None if the model is not available or fails to load.
    """
    # nlp = spacy.load("xx_ent_wiki_sm")
    # import xx_ent_wiki_sm
    # nlp = xx_ent_wiki_sm.load()
    model_name = SPACY_MODELS.get(lang_code)
    if not model_name:
        print(f"No spaCy model available for language code: {lang_code}")
        return None

    if model_name not in loaded_models:
        try:
            ensure_model_installed(model_name)
            loaded_models[model_name] = spacy.load(model_name)
        except Exception as e:  # pylint: disable=broad-except
            print(f"Failed to load spaCy model '{model_name}': {str(e)}")
            return None

    return loaded_models[model_name]


def break_into_sentences(
    plain_text: str,
    word_ids: List[Tuple[int, int]],
    tokenizer: SentenceTokenizer = SentenceTokenizer.SPACY,
    lang_code: str = "en",
) -> Tuple[List[str], Dict[int, int]]:
    """
    Break plain text into sentences and map word IDs to sentence indices.

    Args:
    plain_text (str): The input text without HTML tags.
    word_ids (List[Tuple[int, int]]): List of word start and end indices.
    tokenizer (SentenceTokenizer): Enum to select the tokenizer (SPACY or NLTK).
    lang_code (str): Language code for the text (e.g., 'en' for English, 'fr' for French).

    Returns:
    Tuple[List[str], Dict[int, int]]: A tuple containing:
        - List of sentences
        - Dictionary mapping word index to sentence index
    """
    if tokenizer == SentenceTokenizer.SPACY:
        nlp = get_spacy_model(lang_code)
        if nlp:
            doc = nlp(plain_text)
            sentences = [sent.text for sent in doc.sents]
        else:
            print(f"Falling back to NLTK for language: {lang_code}")
            sentences = sent_tokenize(plain_text)
    elif tokenizer == SentenceTokenizer.NLTK:
        sentences = sent_tokenize(plain_text)
    else:
        raise ValueError(f"Unsupported tokenizer: {tokenizer}")

    word_to_sentence = {}
    current_sentence = 0
    sentence_end = 0

    for i, (word_start, _) in enumerate(word_ids):
        while current_sentence < len(sentences) and word_start >= sentence_end:
            sentence_end += len(sentences[current_sentence])
            current_sentence += 1

        word_to_sentence[i] = current_sentence - 1

    return sentences, word_to_sentence
