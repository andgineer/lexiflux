"""Utility functions for the Django commands."""

import cProfile
import io
import logging
import pstats
from typing import Callable, Any

from django.core.management import CommandError


logger = logging.getLogger(__name__)


def validate_log_level(level_name: str) -> int:
    """Validate the log level and return the corresponding integer value."""
    level = logging.getLevelName(level_name.upper())
    if not isinstance(level, int):
        valid_levels = list(logging._levelToName.values())  # pylint: disable=protected-access
        raise CommandError(
            f"Invalid log level '{level_name}'. Valid options are: {', '.join(valid_levels)}"
        )
    return level


def log_profile(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to log the profile of a function."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        pr = cProfile.Profile()
        pr.enable()
        result = func(*args, **kwargs)
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
        ps.print_stats()
        logger.info(s.getvalue())
        return result

    return wrapper
