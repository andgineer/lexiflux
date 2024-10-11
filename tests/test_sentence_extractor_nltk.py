import allure
import pytest
from lexiflux.language.sentence_extractor import break_into_sentences, SentenceTokenizer


@pytest.fixture
def sample_text_and_word_ids():
    text = " is a test. It has three sentences. How about that? We've"
    word_ids = [
        (1, 3),   # is
        (4, 5),   # a
        (6, 10),  # test
        (11, 13), # It
        (14, 17), # has
        (18, 23), # three
        (24, 33), # sentences
        (35, 38), # How
        (39, 44), # about
        (45, 49), # that
        (51, 55), # We've
    ]
    return text, word_ids


@allure.epic('Book import')
@allure.feature('NLTK: Break text into sentences')
def test_break_into_sentences_nltk(sample_text_and_word_ids):
    text, word_ids = sample_text_and_word_ids
    sentences, word_to_sentence = break_into_sentences(text, word_ids, tokenizer=SentenceTokenizer.NLTK)

    assert sentences == [' is a test.', 'It has three sentences.', 'How about that?', "We've"]
    assert word_to_sentence == {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3}


@allure.epic('Book import')
@allure.feature('NLTK: Break text into sentences')
def test_break_into_sentences_unsupported_language():
    text = "This is a test in an unsupported language."
    word_ids = [(0, 4), (5, 7), (8, 9), (10, 14), (15, 17), (18, 20), (21, 32), (33, 41)]
    sentences, word_to_sentence = break_into_sentences(text, word_ids, tokenizer=SentenceTokenizer.NLTK,
                                                       lang_code='unsupported')

    # Should fall back to NLTK
    assert len(sentences) == 1
    assert sentences[0] == text


@allure.epic('Book import')
@allure.feature('SPACY: Break text into sentences')
def test_break_into_sentences_spacy(sample_text_and_word_ids):
    text, word_ids = sample_text_and_word_ids
    sentences, word_to_sentence = break_into_sentences(text, word_ids, tokenizer=SentenceTokenizer.SPACY)

    assert sentences == [' is a test.', 'It has three sentences.', 'How about that?', "We've"]
    assert word_to_sentence == {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3}
