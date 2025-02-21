"""Management command to show version."""  # noqa: N806

from typing import Any

from django.core.management.base import BaseCommand

from lexiflux import __version__


class Command(BaseCommand):  # type: ignore
    """Show app version."""

    help = "Show app version"

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        self.stdout.write(self.style.SUCCESS(f"Lexiflux: {__version__}"))
