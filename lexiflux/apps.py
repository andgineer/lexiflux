"""Lexiflux app config."""
from typing import Any

from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver


class LexifluxConfig(AppConfig):  # type: ignore
    """Lexiflux app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "lexiflux"

    def ready(self) -> None:
        """Run when the app is ready."""
        import lexiflux.signals  # pylint: disable=import-outside-toplevel,unused-import  # noqa: F401

        @receiver(post_migrate)  # type: ignore
        def populate_languages(sender: Any, **kwargs: Any) -> None:
            # todo move to migration script
            if sender.name == "lexiflux":
                from .dictionary.google_languages import (  # pylint: disable=import-outside-toplevel
                    update_languages,
                )

                update_languages()
