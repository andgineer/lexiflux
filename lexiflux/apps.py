"""Lexiflux app config."""

import logging
from typing import Any

from django.apps import AppConfig

from lexiflux import __version__

logger = logging.getLogger()


class LexifluxConfig(AppConfig):  # type: ignore
    """Lexiflux app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "lexiflux"

    def ready(self) -> None:
        """Run when the app is ready."""
        from django.db.backends.signals import (  # noqa: PLC0415
            connection_created,
        )

        connection_created.connect(self.on_db_connection, dispatch_uid="validate")

    def on_db_connection(self, sender: Any, connection: Any, **kwargs: Any) -> None:  # noqa: ARG002
        """Run when the database connection is created."""
        from lexiflux.lexiflux_settings import settings  # noqa: PLC0415

        try:
            settings.lexiflux.validate()
        except ValueError as e:
            logger.error(f"\n\nLexiflux fail to start:\n{e}")
            raise SystemExit(1) from e
        logger.info(f"Lexiflux {__version__} is ready.")
