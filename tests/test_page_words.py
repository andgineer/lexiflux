import pytest
from lexiflux.models import Book, BookPage, Author, Language


@pytest.fixture
def book_page_with_content(book):
    content = "This is a test page. It contains some words and punctuation!"
    return BookPage.objects.create(number=100, content=content, book=book)


def test_extract_words(book_page_with_content):
    page = book_page_with_content

    with pytest.raises(ValueError):
        text, indices = page.extract_words(0, -1)

    # Test extracting a subset of words
    text, indices = page.extract_words(1, 3)
    assert text == "is a test"
    assert len(indices) == 3

    # Test extracting words with punctuation
    text, indices = page.extract_words(9, 10)
    assert text == "and punctuation"
    assert len(indices) == 2

    # Test invalid range
    with pytest.raises(ValueError):
        page.extract_words(5, 2)

    # Test out of range
    text, indices = page.extract_words(0, 100)
    # excluded punctuation after last word
    assert text == "This is a test page. It contains some words and punctuation"
    assert len(indices) == 11
