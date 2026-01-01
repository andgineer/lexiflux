import re

import allure
import pytest
from unittest.mock import patch, MagicMock, ANY

from pagesmith.page_splitter import PAGE_LENGTH_TARGET

from lexiflux.models import Author, Book, Language
from django.core.management import CommandError
from lexiflux.ebook.book_loader_plain_text import BookLoaderPlainText
from tests.conftest import create_temp_file


@pytest.fixture
def complex_book_text():
    """Generate a complex book text with multiple chapters."""
    chapters = [
        "Chapter 1\n\nFirst chapter content.",
        "Chapter 2\n\nSecond chapter with more text.",
        "Chapter 3\n\nThird chapter with even more text.",
        "Chapter 4\n\nFourth and final chapter.",
    ]

    # Add some space between chapters to force page breaks
    padding = "\n\n" + ". " * 500 + "\n\n"
    return padding.join(chapters)


@allure.epic("Book import")
@allure.feature("Plain text: success import")
@patch("lexiflux.models.Author.objects.get_or_create")
@patch("lexiflux.models.Language.objects.filter")
@patch("lexiflux.models.Book.objects.create")
@patch("lexiflux.models.BookPage.objects.bulk_create")
@patch("lexiflux.models.BookPage.__init__", return_value=None)
def test_import_text_book_success(
    mock_book_page_init,
    mock_book_page_bulk_create,
    mock_book_create,
    mock_language_filter,
    mock_author_get_or_create,
    book_processor_mock,
):
    mock_author_get_or_create.return_value = (MagicMock(spec=Author), True)
    mock_language = MagicMock(spec=Language)
    mock_language_filter.return_value.first.return_value = mock_language

    mock_book = MagicMock(spec=Book)
    mock_book.title = "Test Book"

    mock_book._state = MagicMock()
    mock_book._state.db = None

    mock_book_create.return_value = mock_book

    book_processor_mock.pages = MagicMock(return_value=["Page 1 content", "Page 2 content"])

    book = book_processor_mock.create("")

    assert book.title == "Test Book"

    mock_author_get_or_create.assert_called_once_with(name="Test Author")
    mock_language_filter.assert_called_once_with(name="English")
    mock_book_create.assert_called_once_with(title="Test Book", author=ANY, language=ANY)

    assert mock_book_page_init.call_count == 2

    calls = mock_book_page_init.call_args_list
    assert len(calls) == 2

    call1_kwargs = calls[0][1]
    call2_kwargs = calls[1][1]

    assert call1_kwargs["book"] == mock_book
    assert call1_kwargs["number"] == 1
    assert call1_kwargs["content"] == "Page 1 content"

    assert call2_kwargs["book"] == mock_book
    assert call2_kwargs["number"] == 2
    assert call2_kwargs["content"] == "Page 2 content"

    assert mock_book_page_bulk_create.call_count == 1


@allure.epic("Book import")
@allure.feature("Plain text: failed import")
@patch("lexiflux.models.Book.objects.create")
@patch("lexiflux.models.BookPage.objects.bulk_create")
@patch("lexiflux.models.Author.objects.get_or_create")
@patch("lexiflux.models.Language.objects.filter")
@patch("lexiflux.models.CustomUser.objects.filter")
def test_import_text_book_without_owner_is_public(
    mock_user_filter,
    mock_language_filter,
    mock_author_get_or_create,
    mock_book_page_bulk_create,
    mock_book_create,
    book_processor_mock,
):
    mock_author = MagicMock(spec=Author)
    mock_author._state = MagicMock()
    mock_author._state.db = None
    mock_author_get_or_create.return_value = (mock_author, True)

    mock_language = MagicMock(spec=Language)
    mock_language._state = MagicMock()
    mock_language._state.db = None
    mock_language_filter.return_value.first.return_value = mock_language

    mock_book = MagicMock(spec=Book)
    mock_book._state = MagicMock()
    mock_book._state.db = None
    mock_book.public = False  # Default to false to test that it gets set to true
    mock_book_create.return_value = mock_book

    book_processor_mock.meta = {
        "title": "Test Book",
        "author": "Test Author",
        "language": "English",
    }
    book_processor_mock.pages = MagicMock(return_value=["Page 1 content", "Page 2 content"])

    book = book_processor_mock.create("")

    # Verify that the book is public
    assert book.public is True

    mock_book_create.assert_called_once_with(
        title="Test Book", author=mock_author, language=mock_language
    )


@allure.epic("Book import")
@allure.feature("Plain text: failed import")
@patch("lexiflux.ebook.book_loader_base.CustomUser.objects.filter")
@patch("lexiflux.ebook.book_loader_base.Book.objects.create")
@patch("lexiflux.ebook.book_loader_base.BookPage.objects.create")
@patch("lexiflux.ebook.book_loader_base.Author.objects.get_or_create")
@patch("lexiflux.ebook.book_loader_base.Language.objects.filter")
def test_import_book_nonexistent_owner_email(
    mock_language_filter,
    mock_author_get_or_create,
    mock_book_page_create,
    mock_book_create,
    mock_user_filter,
    book_processor_mock,
):
    mock_user_filter.return_value.first.return_value = None
    mock_author_get_or_create.return_value = (MagicMock(), True)
    mock_language = MagicMock()
    mock_language_filter.return_value.first.return_value = mock_language
    mock_book = MagicMock()
    mock_book_create.return_value = mock_book

    with pytest.raises(CommandError) as exc_info:
        book_processor_mock.create("nonexistent@example.com")

    assert "no such user" in str(exc_info.value)


@allure.epic("Book import")
@allure.feature("Plain text: success import")
@pytest.mark.django_db
def test_import_plain_text_e2e():
    book = BookLoaderPlainText("tests/resources/alice_adventure_in_wonderland.txt").create("")
    assert book.title == "Alice's Adventures in Wonderland"
    assert book.author.name == "Lewis Carroll"
    assert book.language.name == "English"
    assert book.public is True
    assert book.pages.count() == 49
    min_page_len = PAGE_LENGTH_TARGET / 1.5
    max_page_len = PAGE_LENGTH_TARGET * 1.5
    for page in book.pages.all():
        assert page.book == book
        page_text = re.sub(r"[ \t]+", " ", page.content)
        assert max_page_len > len(page_text)
        assert len(page_text) > min_page_len

    with open("tests/resources/alice_1st_page.txt", "r", encoding="utf8") as f:
        assert book.pages.first().content == f.read()
    expected_toc = [
        ("CHAPTER I. Down the Rabbit-Hole", 1, 86),
        ("CHAPTER II. The Pool of Tears", 6, 34),
        ("CHAPTER III. A Caucus-Race and a Long Tale", 10, 135),
        ("CHAPTER IV. The Rabbit Sends in a Little Bill", 14, 100),
        ("CHAPTER V. Advice from a Caterpillar", 19, 264),
        ("CHAPTER VI. Pig and Pepper", 24, 264),
        ("CHAPTER VII. A Mad Tea-Party", 30, 169),
        ("CHAPTER VIII. The Queen’s Croquet-Ground", 35, 400),
        ("CHAPTER IX. The Mock Turtle’s Story", 41, 236),
        ("CHAPTER X. The Lobster Quadrille", 46, 346),
        ("CHAPTER XI. Кто украл the Tarts?", 51, 275),
        ("CHAPTER XII. Alice’s Evidence", 56, 2),
    ]
    book_toc = [tuple(entry) for entry in book.toc]
    # assert book_toc == expected_toc
    for chapter in book.toc[:1]:
        page = book.pages.get(number=chapter[1])
        for word_idx in range(chapter[2] + 10):
            print(f"{word_idx}: {page.content[page.words[word_idx][0] : page.words[word_idx][1]]}")
        print(chapter[0], chapter[1], chapter[2])
        print(page.extract_words(chapter[2], chapter[2] + 4))


@allure.epic("Book import")
@allure.feature("Page splitting")
@pytest.mark.django_db
def test_toc_word_counts_simple(tmpdir):
    """Test that TOC entries have correct chapter position for a simple case."""
    text = """Some introductory text.

Chapter 1

This is the first chapter content."""
    file_path = create_temp_file(text, "utf8", tmpdir)
    book = BookLoaderPlainText(str(file_path)).create("")

    # The TOC should have one entry for Chapter 1
    assert len(book.toc) == 1
    chapter, page_num, word_num = book.toc[0]

    assert chapter == "Chapter 1"
    assert page_num == 1  # First page

    expected_word_count = len("Some introductory text.".split())

    assert word_num == expected_word_count


@allure.epic("Book import")
@allure.feature("Page splitting")
@pytest.mark.django_db
def test_toc_word_counts_multiple_chapters(tmpdir):
    """Test that TOC entries have correct word numbers for multiple chapters."""
    text = """Prologue words here.

Chapter I

First chapter text.

Chapter II

Second chapter text."""

    file_path = create_temp_file(text, "utf8", tmpdir)
    book = BookLoaderPlainText(str(file_path)).create("")

    # The TOC should have two entries
    assert len(book.toc) == 2

    # Check first chapter
    chapter1, page_num1, word_num1 = book.toc[0]
    assert chapter1 == "Chapter I"
    assert page_num1 == 1

    # Words before "Chapter I"
    prologue_words = len("Prologue words here.".split())
    expected_chapter1_word = prologue_words
    assert word_num1 == expected_chapter1_word

    # Check second chapter
    chapter2, page_num2, word_num2 = book.toc[1]
    assert chapter2 == "Chapter II"
    assert page_num2 == 1  # Still on first page

    # Words before "Chapter II" (prologue + first chapter heading + first chapter text)
    first_chapter_text_words = len("First chapter text.".split())
    expected_word_count2 = expected_chapter1_word + len(chapter1.split()) + first_chapter_text_words
    assert word_num2 == expected_word_count2


@allure.epic("Book import")
@allure.feature("Page splitting")
@pytest.mark.django_db
def test_toc_word_counts_across_pages(tmpdir):
    """Test that TOC entries have correct word numbers when chapters span multiple pages."""
    # Create a long text that will span multiple pages
    filler_word_len = len("x ")
    first_page_filler_words_num = int(PAGE_LENGTH_TARGET // filler_word_len * 0.9)

    # Create first page with a chapter at the end closer than target size possible tolerance
    first_page = "x " * first_page_filler_words_num + "\n\nChapter 1\n\n" + "Some text. " * 5

    # Create second page with a chapter even closer to the target size
    second_page = "\n\nChapter 2\n\nMore text."

    text = first_page + second_page

    file_path = create_temp_file(text, "utf8", tmpdir)
    book = BookLoaderPlainText(str(file_path)).create("")

    # The TOC should have two entries
    assert len(book.toc) == 2

    # Check first chapter
    chapter1, page_num1, word_num1 = book.toc[0]
    assert chapter1 == "Chapter 1"
    assert page_num1 == 1  # First page
    assert word_num1 == first_page_filler_words_num

    # Check second chapter
    chapter2, page_num2, word_num2 = book.toc[1]
    assert chapter2 == "Chapter 2"
    assert page_num2 == 2  # Second page
    assert word_num2 == 0


@allure.epic("Book import")
@allure.feature("Page splitting")
@pytest.mark.django_db
def test_toc_integration_with_chapter_detector(tmpdir):
    """Test that PageSplitter correctly integrates with ChapterDetector for word counting."""
    # Text with a chapter
    text = """Intro text.

Chapter 5

Chapter content."""

    file_path = create_temp_file(text, "utf8", tmpdir)
    book = BookLoaderPlainText(str(file_path)).create("")

    assert len(book.toc) == 1
    chapter, page_num, word_num = book.toc[0]

    assert chapter == "Chapter 5"
    assert page_num == 1

    assert word_num == len("Intro text.".split())


@allure.epic("Book import")
@allure.feature("Page splitting")
@pytest.mark.django_db
def test_toc_word_counts_in_complex_book(complex_book_text, tmpdir):
    """Test TOC word counts in a more complex book with multiple pages and chapters."""
    file_path = create_temp_file(complex_book_text, "utf8", tmpdir)
    book = BookLoaderPlainText(str(file_path)).create("")

    # Should have 4 chapters in the TOC
    assert len(book.toc) == 4

    # Check that each chapter is on the correct page
    # and has a reasonable word number
    for i, (chapter, page_num, word_num) in enumerate(book.toc, 1):
        # Chapter title should match pattern
        assert f"Chapter {i}" in chapter

        # Word number should be a non-positive integer
        assert word_num >= 0

        # For chapters after the first, page number should increase
        if i > 1:
            prev_page = book.toc[i - 2][1]
            assert page_num >= prev_page


@allure.epic("Book import")
@allure.feature("Page splitting")
@pytest.mark.django_db
def test_split_inside_p_tag(tmpdir):
    """escape tags when import plain text

    but we have this redundant handle_p_tag_split() in pagesmith that respect <p> tags
    """
    text = "<p>" + "a" * PAGE_LENGTH_TARGET + "</p>" + "b" * (PAGE_LENGTH_TARGET // 2)
    file_path = create_temp_file(text, "utf8", tmpdir)
    book = BookLoaderPlainText(str(file_path)).create("")

    # Assert that the split is inside the <p> tag
    assert book.pages.count() == 2
    assert book.pages.first().content.endswith("&lt;/p&gt;")
    assert book.pages.get(number=2).content.startswith("&lt;p&gt;")
