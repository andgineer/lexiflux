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

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "defaultsecretkey")

# Default to allow all hosts, but replace if LEXIFLUX_ALLOWED_HOSTS is set (comma-separated)
if lexiflux_allowed_hosts := os.environ.get("LEXIFLUX_ALLOWED_HOSTS"):
    ALLOWED_HOSTS = [host.strip() for host in lexiflux_allowed_hosts.split(",") if host.strip()]
else:
    ALLOWED_HOSTS = ["*"]

# Database - SQLite for local Docker (can be mounted as volume)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        "OPTIONS": {
            "timeout": 20,  # Increase timeout to 20 seconds (default is 5)
            "init_command": (
                "PRAGMA journal_mode=WAL;"  # Write-Ahead Logging for better concurrency
                "PRAGMA synchronous=NORMAL;"  # Faster writes, still safe
                "PRAGMA busy_timeout=20000;"  # 20 second busy timeout
                "PRAGMA temp_store=MEMORY;"  # Use memory for temp tables
                "PRAGMA cache_size=-64000;"  # 64MB cache (negative = KB)
            ),
        },
    },
}

# Additional security headers for production-like behavior
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
