import itertools
import logging

import pytest
from unittest.mock import patch


@pytest.mark.django_db
def test_get_language_group(book_plain_text):
    assert book_plain_text.get_language_group('bs') == 'group:bs-hr-sr'
    assert book_plain_text.get_language_group('en') == 'en'


@pytest.mark.django_db
def test_get_random_words(book_plain_text):
    logging.basicConfig(level=logging.DEBUG)
    random_words = book_plain_text.get_random_words(words_num=3)
    assert len(random_words.split()) == 3
    assert random_words.startswith("Word")  # Skipped 1st as potential junk
    assert book_plain_text.get_random_words(words_num=3) != random_words



@pytest.mark.django_db
def test_detect_language(mock_detect_language, book_plain_text):
    # majority in first 3 tries
    mock_detect_language.side_effect = itertools.cycle(['en', 'en', 'fr'])
    assert book_plain_text.detect_language() == 'en'

    # additional tries
    mock_detect_language.side_effect = itertools.cycle(['en', 'de', 'fr', 'de'])
    assert book_plain_text.detect_language() == 'de'

    # one language group no need in additional tries
    mock_detect_language.side_effect = itertools.cycle(['hr', 'sr', 'sr'])
    assert book_plain_text.detect_language() == 'sr'

    # one language group, majority of non-1st language
    mock_detect_language.side_effect = itertools.cycle(['hr', 'sr', 'sr'])
    assert book_plain_text.detect_language() == 'sr'

    # language group, selected by 1st language
    mock_detect_language.side_effect = itertools.cycle(['hr', 'sr', 'en'])
    assert book_plain_text.detect_language() == 'hr'

