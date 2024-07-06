import pytest
from lexiflux.language.extract_sentences import break_into_sentences, SentenceTokenizer, get_spacy_model


@pytest.fixture
def sample_text_and_word_ids():
    text = "This is a test. It has three sentences. How about that?"
    word_ids = [(0, 4), (5, 7), (8, 9), (10, 14), (15, 17), (18, 21), (22, 27),
                (28, 37), (38, 41), (42, 47), (48, 52), (53, 57)]
    return text, word_ids


def test_break_into_sentences_spacy(sample_text_and_word_ids):
    text, word_ids = sample_text_and_word_ids
    sentences, word_to_sentence = break_into_sentences(text, word_ids, tokenizer=SentenceTokenizer.SPACY,
                                                       lang_code='sr')

    assert len(sentences) == 3
    assert sentences[0] == "This is a test."
    assert word_to_sentence == {0: 0, 1: 0, 2: 0, 3: 0, 4: 1, 5: 1, 6: 1, 7: 1, 8: 2, 9: 2, 10: 2, 11: 2}


def test_break_into_sentences_nltk(sample_text_and_word_ids):
    text, word_ids = sample_text_and_word_ids
    sentences, word_to_sentence = break_into_sentences(text, word_ids, tokenizer=SentenceTokenizer.NLTK)

    assert sentences == ["This is a test.", "It has three sentences.", "How about that?"]
    assert word_to_sentence == {0: 0, 1: 0, 2: 0, 3: 0, 4: 1, 5: 1, 6: 1, 7: 1, 8: 2, 9: 2, 10: 2, 11: 2}


def test_break_into_sentences_unsupported_language():
    text = "This is a test in an unsupported language."
    word_ids = [(0, 4), (5, 7), (8, 9), (10, 14), (15, 17), (18, 20), (21, 32), (33, 41)]
    sentences, word_to_sentence = break_into_sentences(text, word_ids, tokenizer=SentenceTokenizer.SPACY,
                                                       lang_code='unsupported')

    # Should fall back to NLTK
    assert len(sentences) == 1
    assert sentences[0] == text


def test_get_spacy_model():
    # Test getting an existing model
    nlp_en = get_spacy_model('en')
    assert nlp_en is not None

    # Test getting a non-existent model
    nlp_nonexistent = get_spacy_model('nonexistent')
    assert nlp_nonexistent is None
