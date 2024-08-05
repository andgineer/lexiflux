"""Lexiflux app config."""

from django.apps import AppConfig


class LexifluxConfig(AppConfig):  # type: ignore
    """Lexiflux app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "lexiflux"

    def ready(self) -> None:
        """Run when the app is ready."""
        import lexiflux.signals  # pylint: disable=import-outside-toplevel,unused-import  # noqa: F401
        from lexiflux.signals import run_startup_tasks  # pylint: disable=import-outside-toplevel
        from lexiflux.lexiflux_settings import settings  # pylint: disable=import-outside-toplevel

        settings.env.validate()
        run_startup_tasks(self)
