from django.core.exceptions import ValidationError
import pytest
from lexiflux.models import Book, BookPage, Author, Language


@pytest.fixture
def book_page_with_content(book):
    content = "This is a test page. It contains some words and punctuation!"
    return BookPage.objects.create(number=100, content=content, book=book)


def test_extract_words(book_page_with_content):
    page = book_page_with_content

    print(f"Page content: {page.content}")
    print(f"Initial word_indices: {page.word_slices}")

    # First access should parse and save words
    words = page.words
    print(f"Words after first access: {words}")
    print(f"word_indices after first access: {page.word_slices}")

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


def test_word_slices_empty_list(book_page_with_content):
    empty_slices = []
    book_page_with_content.word_slices = empty_slices
    book_page_with_content.save()
    assert book_page_with_content.words == empty_slices


def test_word_slices_single_word(book_page_with_content):
    slices = [(0, 4)]
    book_page_with_content.word_slices = slices
    book_page_with_content.save()
    assert book_page_with_content.words == slices


def test_word_slices_multiple_words(book_page_with_content):
    slices = [(0, 4), (5, 7), (8, 9), (10, 14)]
    book_page_with_content.word_slices = slices
    book_page_with_content.save()
    assert book_page_with_content.words == slices


def test_word_slices_large_indices(book_page_with_content):
    slices = [(1000, 1004), (2000, 2010), (3000, 3005)]
    book_page_with_content.word_slices = slices
    book_page_with_content.save()
    assert book_page_with_content.words == slices


def test_word_slices_zero_length_word(book_page_with_content):
    slices = [(0, 0), (1, 1), (2, 2)]
    book_page_with_content.word_slices = slices
    book_page_with_content.save()
    assert book_page_with_content.words == slices


def test_word_slices_overlapping_indices(book_page_with_content):
    slices = [(0, 5), (3, 7), (6, 10)]
    book_page_with_content.word_slices = slices
    book_page_with_content.save()
    assert book_page_with_content.words == slices


def test_word_slices_negative_indices(book_page_with_content):
    slices = [(-5, -1), (0, 5)]
    book_page_with_content.word_slices = slices
    book_page_with_content.save()
    assert book_page_with_content.words == slices


def test_words_property_with_existing_slices(book_page_with_content):
    slices = [(0, 4), (5, 7), (8, 9), (10, 14)]
    book_page_with_content.word_slices = slices
    book_page_with_content.save()
    assert book_page_with_content.words == slices


def test_words_property_with_no_slices(book_page_with_content):
    book_page_with_content.content = "This is a test."
    book_page_with_content.word_slices = None
    book_page_with_content.save()
    words = book_page_with_content.words
    assert len(words) == 4
    assert words == [(0, 4), (5, 7), (8, 9), (10, 14)]


def test_parse_and_save_words(book_page_with_content):
    book_page_with_content.content = "This is another test."
    book_page_with_content._parse_and_save_words()
    assert book_page_with_content.word_slices is not None
    assert len(book_page_with_content.words) == 4
    assert book_page_with_content.words == [(0, 4), (5, 7), (8, 15), (16, 20)]


def test_word_slices_invalid_type(book_page_with_content):
    with pytest.raises(ValidationError):
        book_page_with_content.word_slices = "invalid type"
        book_page_with_content.save()


@pytest.mark.skip(reason="See BooPage.clean()")
def test_word_slices_invalid_structure(book_page_with_content):
    with pytest.raises(ValidationError):
        book_page_with_content.word_slices = [1, 2, 3]  # Not a list of tuples
        book_page_with_content.full_clean()


def test_word_slices_valid_json_invalid_structure(book_page_with_content):
    with pytest.raises(ValidationError):
        book_page_with_content.word_slices = {"key": "value"}  # Valid JSON, invalid structure
        book_page_with_content.full_clean()


@pytest.fixture
def book_page_with_tags(book):
    content = (
        "&#x27;<br/>razgovora? "
        "pre<b>fix</b>word "
        "in&#8211;<i>fix</i> "
        "<i>full</i> "
        "suf<span>fix</span> "
        "&#x22;quo<br/>ted&#x22; "
        "<br/>new<script>hidden</script>line<br/> "
        "multi&#x20;<b>ple</b>&#x20;spaces "
        "<script>hidden</script>visible "
        "&lt;not&#x2D;a&#x2D;tag&gt; "
        "com<i>pl&#233;</i>x"
        """ Hello world <br/> New line-<span id="word-0" class="word">Hello</span> <span id="word-1" class="word">world</span> <br/> <span id="word-2" class="word">New</span> <span id="word-3" class="word">line</span>"""
    )
    return BookPage.objects.create(number=101, content=content, book=book)

def test_words_content_with_tags(book_page_with_tags):
    word_slices = book_page_with_tags.words
    words = [book_page_with_tags.content[start:end] for start, end in word_slices]
    assert words == [
        "razgovora",
        "pre", "fix", "word",
        "in", "fix",
        "full",
        "suf", "fix",
        "quo", "ted",
        "new", "line",
        "multi", "ple", "spaces",
        "visible",
        "not", "a", "tag",
        "com", "pl&#233;", "x",
         'Hello', 'world', 'New', 'line', 'Hello', 'world', 'New', 'line',
    ]