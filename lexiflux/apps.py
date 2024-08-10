"""Lexiflux app config."""

from typing import Any

from django.apps import AppConfig
from lexiflux import __version__


class LexifluxConfig(AppConfig):  # type: ignore
    """Lexiflux app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "lexiflux"

    def ready(self) -> None:
        """Run when the app is ready."""
        from django.db.models.signals import post_migrate  # pylint: disable=import-outside-toplevel

        post_migrate.connect(self.post_migrate_callback, sender=self)

    def post_migrate_callback(self, sender: Any, **kwargs: Any) -> None:  # pylint: disable=unused-argument
        """Callback for post_migrate signal."""
        from lexiflux.lexiflux_settings import settings  # pylint: disable=import-outside-toplevel

        settings.lexiflux.validate()
        print(f"Lexiflux {__version__} is ready.")
