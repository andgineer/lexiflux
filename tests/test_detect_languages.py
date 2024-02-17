import itertools
from io import StringIO
from unittest.mock import patch

import pytest

from lexiflux.ebook.book_plain_text import BookPlainText
from lexiflux.language.translation import detect_language


@pytest.mark.django_db
def test_get_language_group(book_plain_text):
    assert book_plain_text.get_language_group('bs') == 'group:bs-hr-sr'
    assert book_plain_text.get_language_group('en') == 'en'


@pytest.mark.django_db
def test_get_random_words_success(book_plain_text):
    random_words = book_plain_text.get_random_words(words_num=3)
    assert len(random_words.split()) == 3
    assert random_words.startswith("Word")  # Skipped 1st as potential junk
    assert book_plain_text.get_random_words(words_num=3) != random_words


@pytest.mark.django_db
def test_get_random_words_no_separators():
    text = "a"*1000
    words_num = 3
    random_words = BookPlainText(StringIO(text)).get_random_words(words_num=words_num)
    assert len(random_words) == BookPlainText.WORD_ESTIMATED_LENGTH * words_num


@pytest.mark.django_db
def test_detect_language(mock_detect_language, book_plain_text):
    # majority in first 3 tries
    mock_detect_language.reset_mock()
    mock_detect_language.side_effect = itertools.cycle(['en', 'en', 'fr'])
    assert book_plain_text.detect_language() == 'English'
    assert len(mock_detect_language.call_args_list) == 3

    # additional tries
    mock_detect_language.reset_mock()
    mock_detect_language.side_effect = itertools.cycle(['en', 'de', 'fr', 'de', 'de'])
    assert book_plain_text.detect_language() == 'German'
    assert len(mock_detect_language.call_args_list) == 5

    # one language group no need in additional tries
    mock_detect_language.reset_mock()
    mock_detect_language.side_effect = itertools.cycle(['hr', 'sr', 'sr'])
    assert book_plain_text.detect_language() == 'Serbian'
    assert len(mock_detect_language.call_args_list) == 3

    # one language group, majority of non-1st language
    mock_detect_language.reset_mock()
    mock_detect_language.side_effect = itertools.cycle(['hr', 'sr', 'sr'])
    assert book_plain_text.detect_language() == 'Serbian'
    assert len(mock_detect_language.call_args_list) == 3

    # language group, selected by 1st language
    mock_detect_language.reset_mock()
    mock_detect_language.side_effect = itertools.cycle(['hr', 'sr', 'en'])
    assert book_plain_text.detect_language() == 'Croatian'
    assert len(mock_detect_language.call_args_list) == 3

    mock_detect_language.reset_mock()
    mock_detect_language.side_effect = itertools.cycle(['ru', 'fr', 'ru', 'ru'])
    assert book_plain_text.detect_language() == 'Russian'
    assert len(mock_detect_language.call_args_list) == 3


@patch('lexiflux.language.translation.single_detection')
def test_detect_language_key_error(mock_single_detection, monkeypatch, caplog):
    monkeypatch.delenv("DETECTLANGUAGE_API_KEY", raising=False)

    result = detect_language("Test text.")

    assert "Please get you API Key" in caplog.text
    assert result == "en"  # Default fallback language


@patch('lexiflux.language.translation.single_detection')
def test_detect_language_exception(mock_single_detection, monkeypatch, caplog):
    monkeypatch.setenv("DETECTLANGUAGE_API_KEY", "dummy_key")
    # Simulate an exception being raised by single_detection
    mock_single_detection.side_effect = Exception("API failure")

    result = detect_language("Test text.")

    assert "Failed to detect language" in caplog.text
    assert result == "en"  # Default fallback language
