import pytest
from lexiflux.models import Book, BookPage, Author, Language


@pytest.fixture
def book_page_with_content(book):
    content = "This is a test page. It contains some words and punctuation!"
    return BookPage.objects.create(number=100, content=content, book=book)


def test_extract_words(book_page_with_content):
    page = book_page_with_content

    print(f"Page content: {page.content}")
    print(f"Initial word_indices: {page.word_indices}")

    # First access should parse and save words
    words = page.words
    print(f"Words after first access: {words}")
    print(f"word_indices after first access: {page.word_indices}")

    with pytest.raises(ValueError):
        page.extract_words(0, -1)

    # Test extracting a subset of words
    text, indices = page.extract_words(1, 3)
    print(f"Extracted text: {text}")
    print(f"Extracted indices: {indices}")
    assert text == "is a test"
    assert len(indices) == 3

    # Test extracting all words
    text, indices = page.extract_words(0, len(page.words) - 1)
    print(f"Full extracted text: {text}")
    print(f"Full extracted indices: {indices}")
    assert text == page.content[:-1]  # without final punctuation
    assert len(indices) == len(page.words)