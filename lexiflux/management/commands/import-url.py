"""Django management command to import a book from a URL."""  # noqa: N806

import argparse
from typing import Any

from lexiflux.ebook.book_loader_url import BookLoaderURL, CleaningLevel
from lexiflux.management.commands._import_book_base import ImportBookBaseCommand


class Command(ImportBookBaseCommand):  # type: ignore
    """Import a book from a URL."""

    help = "Imports a book from a web page URL"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("url", type=str, help="URL of the web page to import")
        parser.add_argument(
            "-e",
            "--email",
            type=str,
            help="Email of the book owner (if not provided, will try to auto-detect)",
            default=None,
        )
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
            "--public",
            action="store_true",
            help="The book is public and can be read by anyone.",
            default=False,
        )
        parser.add_argument(
            "--language",
            "-f",
            type=str,
            help="Force the language instead of auto-detection. "
            "You can give just a language name start if it's unique.",
            default=None,
        )
        parser.add_argument(
            "--cleaning-level",
            "-c",
            type=str,
            choices=[level.value for level in CleaningLevel],
            help="Content cleaning level: aggressive (extract main content only), "
            "moderate (balanced cleaning), minimal (preserve most content)",
            default=CleaningLevel.MODERATE.value,
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        url = options["url"]
        cleaning_level = CleaningLevel(options["cleaning_level"])
        book_loader = BookLoaderURL(url, cleaning_level=cleaning_level)

        # super() will call self.book_class with path, just ignore that:
        self.book_class = lambda _: book_loader  # type: ignore[assignment]

        options["file_path"] = url
        super().handle(*args, **options)
