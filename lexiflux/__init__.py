"""Lexiflux.

The file is mandatory for build system to find the package.
"""

from lexiflux.__about__ import __version__

__all__ = ["__version__"]
default_app_config = "lexiflux.apps.LexifluxConfig"  # pylint: disable=invalid-name
