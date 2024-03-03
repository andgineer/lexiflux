"""Django management command to import a book from a plain text file."""  # pylint: disable=invalid-name,duplicate-code

import argparse
import logging
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from lexiflux.ebook.book_base import import_book
from lexiflux.ebook.book_plain_text import BookPlainText
from lexiflux.utils import validate_log_level


class Command(BaseCommand):  # type: ignore
    """Import a book from a plain text file."""

    help = "Imports a book from an plain text file"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("file_path", type=str, help="Path to the plain text file to import")
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
            help="""Owner`s email for the book (optional).
 See "list-users" command for a list of users""",
            default=None,
        )
        # todo: search owners by regex and show found if more than one

    def handle(self, *args: Any, **options: Any) -> None:  # pylint: disable=too-many-locals
        file_path = options["file_path"]
        log_level = validate_log_level(options["loglevel"])
        db_log_level = validate_log_level(options["db_loglevel"])
        owner_email = options["owner"]

        # Configure Django logging level
        logging.basicConfig(level=log_level)
        logging.getLogger("django").setLevel(log_level)
        logging.getLogger("django.db.backends").setLevel(db_log_level)

        try:
            book = import_book(BookPlainText(file_path), owner_email)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully imported book "{book.title}" ({book.author}, '
                    f'{book.language}) from "{file_path}", code: {book.code}'
                )
            )
        except Exception as e:
            raise CommandError(f"Error importing book from {file_path}: {e}") from e
