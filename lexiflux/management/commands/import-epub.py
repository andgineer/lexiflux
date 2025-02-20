"""Django management command to import a book from an EPUB file."""  # noqa: N806

from lexiflux.ebook.book_loader_epub import BookLoaderEpub
from lexiflux.management.commands._import_book_base import ImportBookBaseCommand


class Command(ImportBookBaseCommand):  # type: ignore
    """Import a book from an EPUB file."""

    help = "Imports a book from an EPUB file"
    book_class = BookLoaderEpub
