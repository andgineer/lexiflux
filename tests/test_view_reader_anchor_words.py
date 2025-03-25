import allure
import pytest
from lexiflux.views.reader_views import find_closest_word_index, find_closest_word_for_anchor


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.parametrize(
    "positions, target_position, expected_index",
    [
        # Empty positions list
        ([], 10, 0),
        # Target position before first word
        ([(5, 10), (15, 20), (25, 30)], 3, 0),
        # Target position is at first word's start
        ([(5, 10), (15, 20), (25, 30)], 5, 0),
        # Target position is within first word
        ([(5, 10), (15, 20), (25, 30)], 7, 0),
        # Target position is at first word's end
        ([(5, 10), (15, 20), (25, 30)], 10, 0),
        # Target position is between first and second word
        ([(5, 10), (15, 20), (25, 30)], 12, 1),
        # Target position is at second word's start
        ([(5, 10), (15, 20), (25, 30)], 15, 1),
        # Target position is within second word
        ([(5, 10), (15, 20), (25, 30)], 17, 1),
        # Target position is at second word's end
        ([(5, 10), (15, 20), (25, 30)], 20, 1),
        # Target position is between second and third word
        ([(5, 10), (15, 20), (25, 30)], 22, 2),
        # Target position is at last word's start
        ([(5, 10), (15, 20), (25, 30)], 25, 2),
        # Target position is within last word
        ([(5, 10), (15, 20), (25, 30)], 27, 2),
        # Target position is at last word's end
        ([(5, 10), (15, 20), (25, 30)], 30, 2),
        # Target position is after last word
        ([(5, 10), (15, 20), (25, 30)], 35, 2),
        # Non-contiguous words with gaps
        ([(5, 10), (20, 25), (40, 45)], 15, 1),
        # Single word case
        ([(10, 20)], 15, 0),
        # Single word case - before word
        ([(10, 20)], 5, 0),
        # Single word case - after word
        ([(10, 20)], 25, 0),
    ],
)
def test_find_closest_word_index(positions, target_position, expected_index):
    """Test the binary search function to find closest word index."""
    result = find_closest_word_index(positions, target_position)
    assert result == expected_index, f"Expected index {expected_index}, got {result}"


class TestBookPageStub:
    """A stub class for BookPage to use in testing."""

    def __init__(self, content, words, book=None):
        self.content = content
        self.words = words
        self.book = book


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_find_closest_word_for_anchor_with_valid_anchor(book):
    """Test finding the closest word when the anchor exists in the content."""
    # Create content with an anchor
    content = """
    <div>
        <p>This is some text before the anchor.</p>
        <p id="test-anchor">This is the anchor paragraph.</p>
        <p>This is text after the anchor.</p>
    </div>
    """

    # Find positions for testing
    content_start_index = content.find('<p id="test-anchor">')
    anchor_text_start = content.find("This is the anchor paragraph")

    # Create word positions
    words = [
        (10, 20),  # "This is some"
        (30, 40),  # "text before"
        (50, 60),  # "the anchor"
        (content_start_index, content_start_index + 10),  # Part of anchor tag
        (anchor_text_start, anchor_text_start + 10),  # Beginning of anchor text
        (anchor_text_start + 11, anchor_text_start + 20),  # Middle of anchor text
        (200, 210),  # Some text after
    ]

    book_page = TestBookPageStub(content, words, book)

    result = find_closest_word_for_anchor(book_page, "page.html#test-anchor")

    assert result == 3


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_find_closest_word_for_anchor_with_no_anchor(book):
    """Test when the anchor doesn't exist in the content."""
    content = "<div><p>This is some text without the target anchor.</p></div>"
    words = [(5, 10), (15, 20), (25, 30)]

    book_page = TestBookPageStub(content, words, book)

    # Test with a non-existent anchor
    result = find_closest_word_for_anchor(book_page, "page.html#non-existent")

    # Should return 0 when anchor not found
    assert result == 0


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_find_closest_word_for_anchor_with_no_hash(book):
    """Test when the link has no hash/anchor part."""
    content = "<div><p>Some content</p></div>"
    words = [(5, 10), (15, 20)]

    book_page = TestBookPageStub(content, words, book)

    # Test with a link without a hash
    result = find_closest_word_for_anchor(book_page, "page.html")

    # Should return 0 when no hash in link
    assert result == 0


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_find_closest_word_for_anchor_exception_handling(book, monkeypatch):
    """Test that exceptions are handled gracefully."""
    book_page = TestBookPageStub("<div>content</div>", [(5, 10)], book)

    # Replace BeautifulSoup with a function that raises an exception
    def mock_beautiful_soup(*args, **kwargs):
        raise Exception("Test exception")

    monkeypatch.setattr("lexiflux.views.reader_views.BeautifulSoup", mock_beautiful_soup)

    # Should handle exceptions and return 0
    result = find_closest_word_for_anchor(book_page, "page.html#anchor")
    assert result == 0


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_find_closest_word_for_anchor_with_nested_content(book):
    """Test with more complex, nested HTML content."""
    content = """
    <div>
        <h1>Chapter Title</h1>
        <p>First paragraph</p>
        <div id="section1">
            <h2 id="subtitle">Section Subtitle</h2>
            <p>Section content goes here</p>
        </div>
    </div>
    """

    section_start = content.find('<div id="section1">')
    subtitle_start = content.find('<h2 id="subtitle">')
    subtitle_text_start = content.find("Section Subtitle")

    words = [
        (10, 20),  # "Chapter Title"
        (30, 40),  # "First paragraph"
        (section_start, section_start + 10),
        (subtitle_start, subtitle_start + 10),
        (subtitle_text_start, subtitle_text_start + 10),
        (subtitle_text_start + 11, subtitle_text_start + 20),
        (200, 210),  # "Section content"
    ]

    book_page = TestBookPageStub(content, words, book)

    result = find_closest_word_for_anchor(book_page, "page.html#subtitle")

    assert result == 3
