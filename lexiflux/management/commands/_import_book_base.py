"""Django management commands to import books from different file formats."""

import argparse
import logging
import os
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from lexiflux.ebook.book_loader_base import BookLoaderBase
from lexiflux.lexiflux_settings import settings
from lexiflux.models import Language
from lexiflux.utils import validate_log_level

USER_EMAIL_ENV = "LEXIFLUX_USER_EMAIL"


def change_log_level(log_level: int, db_log_level: int) -> None:
    """Change the log level for the command."""
    logging.getLogger().setLevel(log_level)
    logging.getLogger("django").setLevel(log_level)
    logging.getLogger("django.db.backends").setLevel(db_log_level)
    if logging.getLogger().handlers:
        logging.getLogger().handlers[0].setLevel(log_level)
    if logging.getLogger("django").handlers:
        logging.getLogger("django").handlers[0].setLevel(log_level)
    if logging.getLogger("django.db.backends").handlers:
        logging.getLogger("django.db.backends").handlers[0].setLevel(db_log_level)


class ImportBookBaseCommand(BaseCommand):  # type: ignore
    """Base command for importing books from various file formats."""

    help = "Imports a book from a file"
    book_class: type[BookLoaderBase]

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("file_path", type=str, help="Path to the file to import")
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
            help="""The book is public and can be read by anyone.""",
            default=False,
        )
        parser.add_argument(
            "--language",
            "-f",
            type=str,
            help="""Force the language instead of auto-detection.
        You can give a just language name start if its unique.""",
            default=None,
        )

    def get_user_email(self) -> str:
        """Get the email of the system user running the command.
        Raise exception if no user found.
        """
        User = get_user_model()  # noqa: N806
        user_email = os.environ.get(USER_EMAIL_ENV, settings.lexiflux.default_user_email)

        try:
            user = User.objects.get(email=user_email)
            self.stdout.write(f"Auto-detected user email: {user_email}")
        except User.DoesNotExist as e:
            raise CommandError(
                "Could not auto-detect user to set non public book owner. "
                "Please provide it using --email option, "
                f"or set `{USER_EMAIL_ENV}` environment variable.",
            ) from e
        else:
            return user.email  # type: ignore

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        file_path = options["file_path"]
        log_level = validate_log_level(options["loglevel"])
        db_log_level = validate_log_level(options["db_loglevel"])
        public = options["public"]
        email = options["email"]
        forced_language = options["language"]
        if forced_language:
            languages = Language.objects.filter(name__istartswith=forced_language)
            # if more than one language found then print them and exit
            if languages.count() > 1:
                self.stdout.write(
                    self.style.ERROR(
                        f"More than one language found for '--language={forced_language}':",
                    ),
                )
                for language in languages:
                    self.stdout.write(
                        self.style.ERROR(f"  {language.name} ({language.google_code})"),
                    )
                return
            if languages.count() == 0:
                raise CommandError(f"Language '--language={forced_language}' not found")
            forced_language = languages.first().name

        owner_email = None if public else email or self.get_user_email()
        change_log_level(log_level, db_log_level)

        try:
            book = self.book_class(file_path).create(owner_email, forced_language)
            book.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully imported book "{book.title}" ({book.author}, '
                    f'{book.language}) from "{file_path}", code: {book.code}',
                ),
            )
        except Exception as e:
            raise CommandError(f"Error importing book from {file_path}: {e}") from e
