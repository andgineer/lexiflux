"""Utility functions for the Django commands."""

import logging

from django.core.management import CommandError


def validate_log_level(level_name: str) -> int:
    """Validate the log level and return the corresponding integer value."""
    level = logging.getLevelName(level_name.upper())
    if not isinstance(level, int):
        valid_levels = list(logging._levelToName.values())  # pylint: disable=protected-access
        raise CommandError(
            f"Invalid log level '{level_name}'. Valid options are: {', '.join(valid_levels)}"
        )
    return level
