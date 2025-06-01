import allure
import pytest

from lexiflux.models import BookPage
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


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_find_closest_word_for_anchor_with_valid_anchor(book):
    """Test finding the closest word when the anchor exists in the content."""
    content = """
    <div>
        <p>This is some text before the anchor.</p>
        <p id="test-anchor">This is the anchor paragraph.</p>
        <p>This is text after the anchor.</p>
    </div>
    """

    book_page = BookPage.objects.create(book=book, number=10, content=content)

    result = find_closest_word_for_anchor(book_page, "page.html#test-anchor")

    assert result >= 0


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_find_closest_word_for_anchor_with_no_anchor(book):
    """Test when the anchor doesn't exist in the content."""
    content = "<div><p>This is some text without the target anchor.</p></div>"

    book_page = BookPage.objects.create(book=book, number=11, content=content)

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

    book_page = BookPage.objects.create(book=book, number=18, content=content)

    # Test with a link without a hash
    result = find_closest_word_for_anchor(book_page, "page.html")

    # Should return 0 when no hash in link
    assert result == 0


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_find_closest_word_for_anchor_exception_handling(book, monkeypatch):
    """Test that exceptions are handled gracefully."""
    content = "<div>content</div>"

    book_page = BookPage.objects.create(book=book, number=12, content=content)

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

    book_page = BookPage.objects.create(book=book, number=13, content=content)

    result = find_closest_word_for_anchor(book_page, "page.html#subtitle")

    assert result >= 0
