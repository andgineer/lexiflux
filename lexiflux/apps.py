"""Lexiflux app config."""
from django.apps import AppConfig


class LexifluxConfig(AppConfig):  # type: ignore
    """Lexiflux app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "lexiflux"
