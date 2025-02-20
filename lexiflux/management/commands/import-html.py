"""Django management command to import a book from an HTML file."""  # noqa: N806

from lexiflux.ebook.book_loader_html import BookLoaderHtml
from lexiflux.management.commands._import_book_base import ImportBookBaseCommand


class Command(ImportBookBaseCommand):  # type: ignore
    """Import a book from an HTML file."""

    help = "Imports a book from an HTML file"
    book_class = BookLoaderHtml
