"""Django management command to import a book from a plain text file."""  # pylint: disable=invalid-name

from lexiflux.ebook.book_plain_text import BookPlainText

from lexiflux.management.commands._import_book_base import ImportBookBaseCommand


class Command(ImportBookBaseCommand):  # type: ignore
    """Import a book from a plain text file."""

    help = "Imports a book from a plain text file"
    book_class = BookPlainText
