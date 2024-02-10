"""Django management command to import a book from an EPUB file."""  # pylint: disable=invalid-name
import argparse
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from lexiflux.ebook.book_epub import import_book_from_epub  # Adjust the import path as necessary


class Command(BaseCommand):  # type: ignore
    """Import a book from an EPUB file."""

    help = "Imports a book from an EPUB file"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("file_path", type=str, help="Path to the EPUB file to import")

    def handle(self, *args: Any, **options: Any) -> None:
        file_path = options["file_path"]
        try:
            import_book_from_epub(file_path)
            self.stdout.write(self.style.SUCCESS(f'Successfully imported book from "{file_path}"'))
        except Exception as e:
            raise CommandError(f"Error importing book from {file_path}: {e}") from e
