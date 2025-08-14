"""Context processors for Lexiflux."""

from lexiflux.__about__ import __version__


def version_context(request):  # noqa: ARG001
    """Add version information to template context."""
    return {
        "version": __version__,
    }
