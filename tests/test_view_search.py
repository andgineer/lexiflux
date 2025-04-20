import allure
import pytest
from django.urls import reverse

from lexiflux.views.search_view import (
    find_word_boundary,
    get_context_boundaries,
    create_highlighted_context,
)


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_search_functionality_basic(client, approved_user, book):
    client.force_login(approved_user)

    # Create test page with content
    book.pages.all().delete()
    test_content = "This is test content with searchable words"
    book.pages.create(
        number=1,
        content=test_content,
        normalized_content=test_content.lower(),
        word_slices=[(0, 4), (5, 7), (8, 12), (13, 20), (21, 25), (26, 36), (37, 42)],
    )

    # Test basic search
    response = client.post(
        reverse("search"), {"book-code": book.code, "searchInput": "test", "start_page": 1}
    )

    assert response.status_code == 200
    content = response.content.decode()

    # Check for expected elements in response
    assert '<span class="bg-warning">test</span>' in content  # Table header
    assert "<td>1</td>" in content  # Page number
    assert '<span class="bg-warning">test</span>' in content  # Highlighted match


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_search_too_short_term(client, approved_user, book):
    client.force_login(approved_user)

    response = client.post(
        reverse("search"), {"book-code": book.code, "searchInput": "te", "start_page": 1}
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "No results found" in content


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_search_whole_words_only(client, approved_user, book):
    client.force_login(approved_user)

    book.pages.all().delete()
    test_content = "The test is here. Some random words fill testing now. More words around tested case. Last line contains tests end."
    book.pages.create(
        number=1,
        content=test_content,
        normalized_content=test_content.lower(),
        word_slices=[
            (0, 3),
            (4, 8),
            (9, 11),
            (12, 16),
            (17, 21),
            (22, 27),
            (28, 32),
            (33, 40),
            (41, 44),
            (45, 49),
            (50, 55),
            (56, 62),
            (63, 68),
            (69, 73),
            (74, 78),
            (79, 84),
            (85, 88),
        ],
    )

    # Search with whole words off
    response = client.post(
        reverse("search"), {"book-code": book.code, "searchInput": "test", "start_page": 1}
    )
    content = response.content.decode()
    assert response.status_code == 200
    assert content.count("bg-warning") == 4

    # Search with whole words on
    response = client.post(
        reverse("search"),
        {"book-code": book.code, "searchInput": "test", "start_page": 1, "whole-words": "on"},
    )
    content = response.content.decode()
    assert response.status_code == 200
    assert content.count("bg-warning") == 1  # Should only find exact "test"


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_search_from_current_page(client, approved_user, book):
    client.force_login(approved_user)

    book.pages.all().delete()
    # Create multiple pages with content
    book.pages.create(
        number=1,
        content="First test page",
        normalized_content="first test page",
        word_slices=[(0, 5), (6, 10), (11, 15)],
    )
    book.pages.create(
        number=2,
        content="Second test page",
        normalized_content="second test page",
        word_slices=[(0, 6), (7, 11), (12, 16)],
    )

    # Search from page 1
    response = client.post(
        reverse("search"), {"book-code": book.code, "searchInput": "test", "start_page": 1}
    )
    content = response.content.decode()
    assert "<td>1</td>" in content
    assert "<td>2</td>" in content

    # Search from page 2
    response = client.post(
        reverse("search"), {"book-code": book.code, "searchInput": "test", "start_page": 2}
    )
    content = response.content.decode()
    assert "<td>1</td>" not in content
    assert "<td>2</td>" in content


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_search_pagination(client, approved_user, book):
    client.force_login(approved_user)

    book.pages.all().delete()
    # Create more pages than MAX_SEARCH_RESULTS
    for i in range(1, 22):  # Creating 21 pages
        book.pages.create(
            number=i,
            content=f"Test content page {i}",
            normalized_content=f"test content page {i}",
            word_slices=[(0, 4), (5, 12), (13, 17), (18, 20)],
        )

    # Initial search
    response = client.post(
        reverse("search"), {"book-code": book.code, "searchInput": "test", "start_page": 1}
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert content.count("<tr") == 21  # 20 results + 1 spinner row
    assert "spinner-border" in content

    # Load next page
    response = client.post(
        reverse("search"), {"book-code": book.code, "searchInput": "test", "start_page": 21}
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert "<td>21</td>" in content


@allure.epic("Pages endpoints")
@allure.feature("Search")
def test_find_word_boundary_basic():
    """Test basic functionality of finding word boundaries."""
    text = "This is a test string with some words."

    # Test finding start boundary
    start_pos = find_word_boundary(text, 7, -1)  # Position in the middle of 'a'
    assert start_pos == 7  # Position doesn't change

    # Test finding end boundary
    end_pos = find_word_boundary(text, 7, 1)  # Position in the middle of 'a'
    assert end_pos == 7  # Position doesn't change


@allure.epic("Pages endpoints")
@allure.feature("Search")
def test_find_word_boundary_punctuation():
    """Test finding word boundaries with punctuation."""
    text = "Hello, world! This is a test."

    # Test with comma
    start_pos = find_word_boundary(text, 5, -1)  # Position of comma
    assert start_pos == 0  # Expected to find the start of 'Hello'

    end_pos = find_word_boundary(text, 5, 1)  # Position of comma
    assert end_pos == 6  # Expected to find position after comma

    # Test with space after punctuation
    start_pos = find_word_boundary(text, 7, -1)  # Position in 'world'
    assert start_pos == 6  # Finds the position after comma (before 'world')

    # Test with exclamation mark
    end_pos = find_word_boundary(text, 12, 1)  # Position of exclamation mark
    assert end_pos == 13  # Expected to find position after exclamation


@allure.epic("Pages endpoints")
@allure.feature("Search")
def test_find_word_boundary_edge_cases():
    """Test edge cases for find_word_boundary."""
    text = "Word"

    # Test at start of string
    start_pos = find_word_boundary(text, 0, -1)
    assert start_pos == 0  # Expected to stay at start

    # Test at end of string
    end_pos = find_word_boundary(text, 3, 1)
    assert end_pos == 3  # Expected to stay at end position

    # Test with empty string
    text = ""
    start_pos = find_word_boundary(text, 0, -1)
    assert start_pos == 0  # Expected to stay at start of empty string


@allure.epic("Pages endpoints")
@allure.feature("Search")
def test_get_context_boundaries_basic():
    """Test basic functionality of getting context boundaries."""
    text = "This is a test string with some words in it. This is a second sentence."
    word_start = 10  # Position in 'string'
    word_end = 16  # End of 'string'
    context_len = 5

    start, end = get_context_boundaries(text, word_start, word_end, context_len)
    expected_context = text[start:end]
    # Basic check that we're getting context around the word
    assert "test" in expected_context
    assert "string" in expected_context


@allure.epic("Pages endpoints")
@allure.feature("Search")
def test_get_context_boundaries_at_start():
    """Test getting context when the word is near the start."""
    text = "This is a test string with some words."
    word_start = 0  # Start of 'This'
    word_end = 4  # End of 'This'
    context_len = 5

    start, end = get_context_boundaries(text, word_start, word_end, context_len)
    assert start == 0  # Should start at beginning
    assert "This is a test" in text[start:end]


@allure.epic("Pages endpoints")
@allure.feature("Search")
def test_get_context_boundaries_at_end():
    """Test getting context when the word is near the end."""
    text = "This is a test string with some words."
    word_start = 32  # Start of 'words'
    word_end = 37  # End of 'words'
    context_len = 5

    start, end = get_context_boundaries(text, word_start, word_end, context_len)
    assert end == 37  # Ends at the end of 'words', not including period
    assert "with some words" in text[start:end]


@allure.epic("Pages endpoints")
@allure.feature("Search")
def test_create_highlighted_context_basic():
    """Test basic functionality of highlighting context."""
    text = "This is a test string with some words."

    # Character positions for "a test"
    start_pos = 8
    term_length = 6

    highlighted = create_highlighted_context(text, start_pos, term_length)
    assert 'This is <span class="bg-warning">a test</span> string with some words.' == highlighted


@allure.epic("Pages endpoints")
@allure.feature("Search")
def test_create_highlighted_context_multiple_words():
    """Test highlighting multiple occurrences of a word."""
    text = "This test is a test string with test words."

    # Highlight first "test" with correct character positions
    start_pos1 = 5
    term_length1 = 4
    highlighted = create_highlighted_context(text, start_pos1, term_length1)
    assert (
        'This <span class="bg-warning">test</span> is a test string with test words.' == highlighted
    )

    # Highlight "s a" with correct character positions
    start_pos2 = 11
    term_length2 = 3
    highlighted = create_highlighted_context(text, start_pos2, term_length2)
    assert (
        'This test i<span class="bg-warning">s a</span> test string with test words.' == highlighted
    )


@allure.epic("Pages endpoints")
@allure.feature("Search")
def test_create_highlighted_context_at_boundaries():
    """Test highlighting at string boundaries."""
    text = "Test string with test at end"

    # Test at start
    highlighted = create_highlighted_context(text, 0, 4)
    assert '<span class="bg-warning">Test</span> string with test at end' == highlighted

    # Test at end - correct positions for " tes"
    highlighted = create_highlighted_context(text, 17, 4)
    assert 'Test string with <span class="bg-warning">test</span> at end' == highlighted
