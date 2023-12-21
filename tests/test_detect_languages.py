import itertools

import pytest
from unittest.mock import patch, mock_open
from lexiflux.ebook.book_plain_text import BookPlainText  # Replace with the actual module name
from lexiflux.models import Language


@pytest.fixture
def book_plain_text():
    # Mock the file reading part
    with patch("builtins.open", mock_open(
            read_data=(
                    "Word1 Word2 Word3 Word4 Word5 Word6 Word7 Word8 Word9 "
                    "Word10 Word11 Word12 Word13 Word14 Word15 Word16 Word17"
            )
    )):
        return BookPlainText("dummy_path")


@pytest.mark.django_db
def test_get_language_group(book_plain_text):
    assert book_plain_text.get_language_group('bs') == 'group:bs-hr-sr'
    assert book_plain_text.get_language_group('en') == 'en'
    # Add more assertions for different languages and groups


@pytest.mark.django_db
def test_get_random_words(book_plain_text):
    random_words = book_plain_text.get_random_words()
    assert len(random_words.split()) == 15
    assert random_words.startswith("Word2")  # Skipped 1st as junk
    # You can add more assertions to check the randomness, length, etc.


@pytest.mark.django_db
@patch('lexiflux.ebook.book_plain_text.detect_language')
def test_detect_language(mock_detect_language, book_plain_text):
    Language.objects.create(name='English2', google_code='en2', epub_code='eng')
    Language.objects.create(name='Bosnian2', google_code='bs2', epub_code='bos')

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

