"""Django management command to import a book from an EPUB file."""  # pylint: disable=invalid-name

from lexiflux.management.commands._import_book_base import ImportBookBaseCommand
from lexiflux.ebook.book_loader_epub import BookLoaderEpub


class Command(ImportBookBaseCommand):  # type: ignore
    """Import a book from an EPUB file."""

    help = "Imports a book from an EPUB file"
    book_class = BookLoaderEpub
