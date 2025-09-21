"""
Local development settings for Lexiflux.

These settings replicate the current local development environment:
- SQLite database
- Debug mode enabled
- Auto-login enabled
- All AI models available including Ollama
"""

from .base import *  # noqa: F401,F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
DEBUGGER_TOOLBAR = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-(qy1)@^p*1x^l$ayy@(t-5cym8y5a#8e0jrlr2v#sprhv)cei#"  # noqa: S105

ALLOWED_HOSTS: list[str] = [
    "localhost",
    "127.0.0.1",
    "host.docker.internal",
    "lexiflux.ai",
]

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    },
}

# Debug toolbar configuration (if enabled)
if DEBUGGER_TOOLBAR:
    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    # Debug middleware should be after all system middleware but before custom middleware
    MIDDLEWARE.insert(-1, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1"]
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda _request: True,
    }
