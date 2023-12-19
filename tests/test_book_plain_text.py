import pytest
from io import StringIO
from lexiflux.ebook.book_plain_text import BookPlainText


@pytest.fixture
def mock_page_splitter():
    original_target = BookPlainText.PAGE_LENGTH_TARGET
    BookPlainText.PAGE_LENGTH_TARGET = 30  # Mocked target length for testing
    BookPlainText.PAGE_MIN_LENGTH = int(BookPlainText.PAGE_LENGTH_TARGET * (1 - BookPlainText.PAGE_LENGTH_ERROR_TOLERANCE))
    BookPlainText.PAGE_MAX_LENGTH = int(BookPlainText.PAGE_LENGTH_TARGET * (1 + BookPlainText.PAGE_LENGTH_ERROR_TOLERANCE))
    yield
    BookPlainText.PAGE_LENGTH_TARGET = original_target  # Reset to original after tests
    BookPlainText.PAGE_MIN_LENGTH = int(BookPlainText.PAGE_LENGTH_TARGET * (1 - BookPlainText.PAGE_LENGTH_ERROR_TOLERANCE))
    BookPlainText.PAGE_MAX_LENGTH = int(BookPlainText.PAGE_LENGTH_TARGET * (1 + BookPlainText.PAGE_LENGTH_ERROR_TOLERANCE))


def test_paragraph_end_priority(mock_page_splitter):
    # Paragraph end is within 25% error margin but farther than sentence end
    text = "a" * 25 + ".  " + 'b' * 5 + "\n\n" + "a"*22 + "\r\n\t\r\n" + "b" * 3 + ". \r" + "a" * 10
    splitter = BookPlainText(StringIO(text))
    pages = list(splitter.pages())
    assert len(pages) == 3
    assert "a" * 25 + ". " + 'b' * 5 + "<br/><br/>" == pages[0]
    assert "a"*22 + "<br/> <br/>" == pages[1]
    assert "b" * 3 + ". " + "a" * 10 == pages[2]


def test_sentence_end_priority(mock_page_splitter):
    # Sentence end near farther than word end
    text = "a" * 23 + ". " + 'b' * 5 + " next  sentence."
    splitter = BookPlainText(StringIO(text))
    pages = list(splitter.pages())
    assert len(pages) == 2
    assert "a" * 23 + ". " == pages[0]
    assert 'b' * 5 + " next sentence." == pages[1]


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


def test_chapter_pattern(mock_page_splitter, chapter_pattern):
    splitter = BookPlainText(StringIO(f"aa{chapter_pattern}34"))
    list(splitter.pages())
    assert splitter.headings[0] == (chapter_pattern.replace("\n", " ").strip(), "1:2")
