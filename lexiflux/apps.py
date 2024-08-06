"""Lexiflux app config."""

from django.apps import AppConfig


class LexifluxConfig(AppConfig):  # type: ignore
    """Lexiflux app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "lexiflux"

    def ready(self) -> None:
        """Run when the app is ready."""
        from lexiflux.lexiflux_settings import settings  # pylint: disable=import-outside-toplevel

        settings.env.validate()
