import allure
import pytest
from unittest.mock import patch, MagicMock, ANY

from lexiflux.models import Author, Book, Language
from django.core.management import CommandError
from lexiflux.ebook.book_loader_plain_text import BookLoaderPlainText


@allure.epic("Book import")
@allure.feature("Plain text: success import")
@patch("lexiflux.models.Author.objects.get_or_create")
@patch("lexiflux.models.Language.objects.get_or_create")
@patch("lexiflux.models.Book.objects.create")
@patch("lexiflux.models.BookPage.objects.bulk_create")
@patch("lexiflux.models.BookPage.__init__", return_value=None)
def test_import_text_book_success(
    mock_book_page_init,
    mock_book_page_bulk_create,
    mock_book_create,
    mock_language_get_or_create,
    mock_author_get_or_create,
    book_processor_mock,
):
    mock_author_get_or_create.return_value = (MagicMock(spec=Author), True)
    mock_language_get_or_create.return_value = (MagicMock(spec=Language), True)

    mock_book = MagicMock(spec=Book)
    mock_book.title = "Test Book"

    mock_book._state = MagicMock()
    mock_book._state.db = None

    mock_book_create.return_value = mock_book

    book_processor_mock.pages = MagicMock(return_value=["Page 1 content", "Page 2 content"])

    book = book_processor_mock.create("")

    assert book.title == "Test Book"

    mock_author_get_or_create.assert_called_once_with(name="Test Author")
    mock_language_get_or_create.assert_called_once_with(name="English")
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
@patch("lexiflux.models.Language.objects.get_or_create")
@patch("lexiflux.models.CustomUser.objects.filter")
def test_import_text_book_without_owner_is_public(
    mock_user_filter,
    mock_language_get_or_create,
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
    mock_language_get_or_create.return_value = (mock_language, True)

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
@patch("lexiflux.ebook.book_loader_base.Language.objects.get_or_create")
def test_import_book_nonexistent_owner_email(
    mock_language_get_or_create,
    mock_author_get_or_create,
    mock_book_page_create,
    mock_book_create,
    mock_user_filter,
    book_processor_mock,
):
    mock_user_filter.return_value.first.return_value = None
    mock_author_get_or_create.return_value = (MagicMock(), True)
    mock_language_get_or_create.return_value = (MagicMock(), True)
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
    assert book.pages.count() == 61
    with open("tests/resources/alice_1st_page.txt", "r", encoding="utf8") as f:
        assert book.pages.first().content == f.read()
    expected_toc = [
        ("CHAPTER I.   Down the Rabbit-Hole", 1, 86),
        ("CHAPTER II.   The Pool of Tears", 6, 34),
        ("CHAPTER III.   A Caucus-Race and a Long Tale", 10, 135),
        ("CHAPTER IV.   The Rabbit Sends in a Little Bill", 14, 100),
        ("CHAPTER V.   Advice from a Caterpillar", 19, 264),
        ("CHAPTER VI.   Pig and Pepper", 24, 264),
        ("CHAPTER VII.   A Mad Tea-Party", 30, 169),
        ("CHAPTER VIII.   The Queen’s Croquet-Ground", 35, 400),
        ("CHAPTER IX.   The Mock Turtle’s Story", 41, 236),
        ("CHAPTER X.   The Lobster Quadrille", 46, 346),
        ("CHAPTER XI.   Кто украл the Tarts?", 51, 275),
        ("CHAPTER XII.   Alice’s Evidence", 56, 2),
    ]
    assert book.toc == expected_toc
