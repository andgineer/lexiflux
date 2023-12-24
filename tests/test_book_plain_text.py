import pytest
from io import StringIO
from lexiflux.ebook.book_plain_text import BookPlainText


@pytest.fixture
def mock_page_splitter():
    yield from mock_book_plain_text(30)


@pytest.fixture
def mock_page100_splitter():
    yield from mock_book_plain_text(100)


def mock_book_plain_text(page_length: int):
    original_target = BookPlainText.PAGE_LENGTH_TARGET
    set_book_page_length(page_length)
    yield
    set_book_page_length(original_target)


def set_book_page_length(page_length):
    BookPlainText.PAGE_LENGTH_TARGET = page_length  # Mocked target length for testing
    BookPlainText.PAGE_LENGTH_ERROR_TOLERANCE = 0.5
    BookPlainText.PAGE_MIN_LENGTH = int(
        BookPlainText.PAGE_LENGTH_TARGET * (1 - BookPlainText.PAGE_LENGTH_ERROR_TOLERANCE))
    BookPlainText.PAGE_MAX_LENGTH = int(
        BookPlainText.PAGE_LENGTH_TARGET * (1 + BookPlainText.PAGE_LENGTH_ERROR_TOLERANCE))


def test_paragraph_end_priority(mock_page_splitter):
    # Paragraph end is within 25% error margin but farther than sentence end
    text = "a" * 25 + ".  " + 'b' * 5 + "\n\n" + "a"*22 + "\r\n\t\r\n" + "b" * 3 + ". \r" + "a" * 10
    splitter = BookPlainText(StringIO(text))
    pages = list(splitter.pages())
    assert len(pages) == 3
    assert "a" * 25 + ". " + 'b' * 5 == pages[0]
    assert " <br/> <br/> " + "a"*22 == pages[1]
    assert " <br/> <br/> " + "b" * 3 + ". " + "a" * 10 == pages[2]


def test_sentence_end_priority(mock_page_splitter):
    # Sentence end near farther than word end
    text = "a" * 29 + " aaa" + ". " + 'b' * 5 + " next  sentence.\n"
    splitter = BookPlainText(StringIO(text))
    pages = list(splitter.pages())
    assert len(pages) == 3
    assert "a" * 29 + " aaa" + ". " == pages[0]

    # now no sentence - will split nearer to target by words
    text = "a" * 29 + " aaa" + "  " + 'b' * 5 + " next  sentence.\n"
    splitter = BookPlainText(StringIO(text))
    pages = list(splitter.pages())
    assert len(pages) == 3
    assert "a" * 29 == pages[0]


def test_word_end_priority(mock_page_splitter):
    # No paragraph or sentence end, splitting by word
    text = "A long text without special ends here"
    splitter = BookPlainText(StringIO(text))
    pages = list(splitter.pages())
    assert len(pages) == 2


def test_no_special_end(mock_page_splitter):
    # A long string without any special end
    text = "a"*60
    splitter = BookPlainText(StringIO(text))
    pages = list(splitter.pages())
    assert len(pages) == 2
    len(pages[0]) == 30


def test_chapter_pattern(mock_page100_splitter, chapter_pattern):
    splitter = BookPlainText(StringIO(f"aa{chapter_pattern}34"))
    pages = list(splitter.pages())
    assert len(splitter.headings) == 1, f"chapter_pattern: {chapter_pattern}"
    assert splitter.headings[0] == (chapter_pattern.replace("\n", "   ").strip(), "1:2:2")


def test_wrong_chapter_pattern(mock_page_splitter, wrong_chapter_pattern):
    splitter = BookPlainText(StringIO(f"aa{wrong_chapter_pattern}34"))
    list(splitter.pages())
    assert len(splitter.headings) == 0, f"chapter_pattern: {wrong_chapter_pattern}"


def test_pages_shift_if_heading(mock_page_splitter):
    chapter_pattern = "\n\nCHAPTER VII.\n\n"
    splitter = BookPlainText(StringIO("a"*16 + chapter_pattern))
    pages = list(splitter.pages())
    assert len(pages) == 3
    assert pages[0] == "a"*16

    splitter = BookPlainText(StringIO("a" * 20 + "aa\n\n" + "d" * 21 + "\n\n34"))
    pages = list(splitter.pages())
    assert len(pages) == 3
    assert pages[0] == "a" * 20 + "aa"
