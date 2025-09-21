"""
Docker local development settings for Lexiflux.

These settings are for running Lexiflux in a local Docker container:
- SQLite database (stored in container/volume)
- Debug mode disabled for production-like behavior
- Auto-login enabled for convenience
- Ollama included for local AI model testing
- UI settings restricted (LEXIFLUX_UI_SETTINGS_ONLY=true)
"""

import os

from .base import *  # noqa: F401,F403

# Debug mode for simple static file serving
DEBUG = True

# Environment variables from Dockerfile
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "defaultsecretkey")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

# Database - SQLite for local Docker (can be mounted as volume)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    },
}

# Additional security headers for production-like behavior
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
