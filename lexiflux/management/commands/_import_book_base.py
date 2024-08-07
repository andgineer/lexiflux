"""Django management commands to import books from different file formats."""

import argparse
import logging
from typing import Any, Type

from django.core.management.base import BaseCommand, CommandError

from lexiflux.ebook.book_base import import_book, BookBase
from lexiflux.utils import validate_log_level


class ImportBookBaseCommand(BaseCommand):  # type: ignore
    """Base command for importing books from various file formats."""

    help = "Imports a book from a file"
    book_class: Type[BookBase]

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("file_path", type=str, help="Path to the file to import")
        parser.add_argument(
            "-l",
            "--loglevel",
            type=str,
            help="Logging level for the command",
            default="INFO",
        )
        parser.add_argument(
            "--ld",
            "--db-loglevel",
            dest="db_loglevel",
            type=str,
            help="Logging level for Django ORM",
            default="INFO",
        )
        parser.add_argument(
            "--owner",
            type=str,
            help="""Owner's email for the book (optional).
 See "list-users" command for a list of users""",
            default=None,
        )
        # todo: search owners by regex and show found if more than one

    def handle(self, *args: Any, **options: Any) -> None:
        file_path = options["file_path"]
        log_level = validate_log_level(options["loglevel"])
        db_log_level = validate_log_level(options["db_loglevel"])
        owner_email = options["owner"]

        # Configure Django logging level
        logging.basicConfig(level=log_level)
        logging.getLogger("django").setLevel(log_level)
        logging.getLogger("django.db.backends").setLevel(db_log_level)

        try:
            book = import_book(self.book_class(file_path), owner_email)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully imported book "{book.title}" ({book.author}, '
                    f'{book.language}) from "{file_path}", code: {book.code}'
                )
            )
        except Exception as e:
            raise CommandError(f"Error importing book from {file_path}: {e}") from e
