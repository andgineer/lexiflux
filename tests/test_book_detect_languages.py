import itertools
from io import StringIO

import allure
import pytest

from lexiflux.ebook.book_loader_plain_text import BookLoaderPlainText


@allure.epic('Book import')
@allure.feature('Plain text: Language detection')
@pytest.mark.django_db
def test_get_language_group(book_plain_text):
    assert book_plain_text.get_language_group('bs') == 'group:bs-hr-sr'
    assert book_plain_text.get_language_group('en') == 'en'


@allure.epic('Book import')
@allure.feature('Plain text: Language detection')
@pytest.mark.django_db
@pytest.mark.django_db
def test_get_random_words_success(book_plain_text):
    MAX_ATTEMPTS = 5
    WORDS_NUM = 3

    for _ in range(MAX_ATTEMPTS):
        random_words_1 = book_plain_text.get_random_words(words_num=WORDS_NUM)
        random_words_2 = book_plain_text.get_random_words(words_num=WORDS_NUM)

        assert len(random_words_1.split()) == WORDS_NUM
        assert random_words_1.startswith("Word")  # Skipped 1st as potential junk

        if random_words_1 != random_words_2:
            # Test passes if we find different results
            return

    # If we get here, the test failed all attempts
    pytest.fail(f"get_random_words returned the same result in {MAX_ATTEMPTS} attempts")


@allure.epic('Book import')
@allure.feature('Plain text: Language detection')
@pytest.mark.django_db
def test_get_random_words_no_separators():
    text = "a"*1000
    words_num = 3
    random_words = BookLoaderPlainText(StringIO(text)).get_random_words(words_num=words_num)
    assert len(random_words) == BookLoaderPlainText.WORD_ESTIMATED_LENGTH * words_num


@allure.epic('Book import')
@allure.feature('Plain text: Language detection')
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

