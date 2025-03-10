import allure
import pytest
from unittest.mock import patch, MagicMock, call, ANY

from lexiflux.models import Author, Book, Language
from django.core.management import CommandError
from lexiflux.ebook.book_loader_plain_text import BookLoaderPlainText


@allure.epic("Book import")
@allure.feature("Plain text: success import")
@patch("lexiflux.models.Author.objects.get_or_create")
@patch("lexiflux.models.Language.objects.get_or_create")
@patch("lexiflux.models.Book.objects.create")
@patch("lexiflux.models.BookPage.objects.create")
def test_import_book_success(
    mock_book_page_create,
    mock_book_create,
    mock_language_get_or_create,
    mock_author_get_or_create,
    book_processor_mock,
):
    mock_author_get_or_create.return_value = (MagicMock(spec=Author), True)
    mock_language_get_or_create.return_value = (MagicMock(spec=Language), True)

    mock_book = MagicMock(spec=Book)
    mock_book.title = "Test Book"
    mock_book_create.return_value = mock_book

    book = book_processor_mock.create("")

    assert book.title == "Test Book"

    # Verify that all mocks were called as expected
    mock_author_get_or_create.assert_called_once_with(name="Test Author")
    mock_language_get_or_create.assert_called_once_with(name="English")
    mock_book_create.assert_called_once_with(title="Test Book", author=ANY, language=ANY)

    # Since we're not specifying the exact content of pages in this example,
    # and they're generated by the book_processor_mock, we expect at least two calls
    # with any arguments for creating book pages.
    assert mock_book_page_create.call_count == 2

    expected_calls = [
        call(book=mock_book, number=1, content="Page 1 content"),
        call(book=mock_book, number=2, content="Page 2 content"),
    ]
    mock_book_page_create.assert_has_calls(expected_calls, any_order=True)


@allure.epic("Book import")
@allure.feature("Plain text: failed import")
@patch("lexiflux.models.CustomUser.objects.filter")
@patch("lexiflux.models.Book.objects.create")
@patch("lexiflux.models.BookPage.objects.create")
@patch("lexiflux.models.Author.objects.get_or_create")
@patch("lexiflux.models.Language.objects.get_or_create")
def test_import_book_without_owner_is_public(
    mock_language_get_or_create,
    mock_author_get_or_create,
    mock_book_page_create,
    mock_book_create,
    mock_user_filter,
    book_processor_mock,
):
    mock_book = MagicMock(spec=Book)
    mock_book_create.return_value = mock_book
    mock_author_get_or_create.return_value = (MagicMock(), True)
    mock_language_get_or_create.return_value = (MagicMock(), True)

    book = book_processor_mock.create("")
    assert book.public is True


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
