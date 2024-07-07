import json

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


def test_encode_decode_empty_list(book_page_with_content):
    empty_indices = []
    book_page_with_content.word_indices = book_page_with_content._encode_word_indices(empty_indices)
    decoded = book_page_with_content._decode_word_indices()
    assert decoded == empty_indices


def test_encode_decode_single_word(book_page_with_content):
    indices = [(0, 4)]
    book_page_with_content.word_indices = book_page_with_content._encode_word_indices(indices)
    decoded = book_page_with_content._decode_word_indices()
    assert decoded == indices


def test_encode_decode_multiple_words(book_page_with_content):
    indices = [(0, 4), (5, 7), (8, 9), (10, 14)]
    encoded = book_page_with_content._encode_word_indices(indices)
    book_page_with_content.word_indices = encoded
    decoded = book_page_with_content._decode_word_indices()
    assert decoded == indices


def test_encode_decode_large_indices(book_page_with_content):
    indices = [(1000, 1004), (2000, 2010), (3000, 3005)]
    encoded = book_page_with_content._encode_word_indices(indices)
    book_page_with_content.word_indices = encoded
    decoded = book_page_with_content._decode_word_indices()
    assert decoded == indices


def test_encode_decode_zero_length_word(book_page_with_content):
    indices = [(0, 0), (1, 1), (2, 2)]
    encoded = book_page_with_content._encode_word_indices(indices)
    book_page_with_content.word_indices = encoded
    decoded = book_page_with_content._decode_word_indices()
    assert decoded == indices


def test_encode_decode_overlapping_indices(book_page_with_content):
    indices = [(0, 5), (3, 7), (6, 10)]
    encoded = book_page_with_content._encode_word_indices(indices)
    book_page_with_content.word_indices = encoded
    decoded = book_page_with_content._decode_word_indices()
    assert decoded == indices


def test_decode_invalid_json(book_page_with_content):
    book_page_with_content.word_indices = "invalid json"
    decoded = book_page_with_content._decode_word_indices()
    assert decoded == []


def test_decode_odd_number_of_elements(book_page_with_content):
    book_page_with_content.word_indices = json.dumps([1, 2, 3])
    with pytest.raises(ValueError):
        book_page_with_content._decode_word_indices()


def test_encode_decode_negative_indices(book_page_with_content):
    indices = [(-5, -1), (0, 5)]
    encoded = book_page_with_content._encode_word_indices(indices)
    book_page_with_content.word_indices = encoded
    decoded = book_page_with_content._decode_word_indices()
    assert decoded == indices


def test_words_property_with_existing_indices(book_page_with_content):
    indices = [(0, 4), (5, 7), (8, 9), (10, 14)]
    book_page_with_content.word_indices = book_page_with_content._encode_word_indices(indices)
    assert book_page_with_content.words == indices


def test_words_property_with_no_indices(book_page_with_content):
    book_page_with_content.content = "This is a test."
    book_page_with_content.word_indices = None
    words = book_page_with_content.words
    assert len(words) == 4
    assert words == [(0, 4), (5, 7), (8, 9), (10, 14)]


def test_parse_and_save_words(book_page_with_content):
    book_page_with_content.content = "This is another test."
    book_page_with_content._parse_and_save_words()
    assert book_page_with_content.word_indices is not None
    assert len(book_page_with_content.words) == 4
    assert book_page_with_content.words == [(0, 4), (5, 7), (8, 15), (16, 20)]