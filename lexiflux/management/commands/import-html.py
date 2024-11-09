"""Django management command to import a book from an HTML file."""  # pylint: disable=invalid-name

from lexiflux.management.commands._import_book_base import ImportBookBaseCommand
from lexiflux.ebook.book_loader_html import BookLoaderHtml


class Command(ImportBookBaseCommand):  # type: ignore
    """Import a book from an HTML file."""

    help = "Imports a book from an HTML file"
    book_class = BookLoaderHtml
