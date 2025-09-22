"""
Koyeb production settings for Lexiflux.

These settings are for deploying Lexiflux on Koyeb cloud platform:
- PostgreSQL database via DATABASE_URL
- Production security settings
- Social authentication required (no auto-login)
- Ollama disabled (memory constraints)
- Proper static file configuration
"""

import os

import dj_database_url

from .base import *  # noqa: F401,F403

# Production security settings
DEBUG = False
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required for Koyeb deployment")

# Domain configuration
ALLOWED_HOSTS = [
    "lexiflux.sorokin.engineer",
    "*.koyeb.app",  # Allow Koyeb subdomains
    "localhost",  # For local testing
]

# Database - PostgreSQL via DATABASE_URL
DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL", ""),
        conn_max_age=600,
        conn_health_checks=True,
    ),
}

if not DATABASES["default"]:
    raise ValueError("DATABASE_URL environment variable is required for Koyeb deployment")

# Static files configuration with WhiteNoise
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
STATICFILES_DIRS = [
    BASE_DIR / "lexiflux" / "static",  # noqa: F405
]

# WhiteNoise for static file serving in production
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Add WhiteNoise middleware for static file serving
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Must be after SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "lexiflux.middleware.ExceptionJSONResponseMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    # AutoLoginMiddleware removed for production
]

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"

# Force HTTPS in production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Enhanced social authentication configuration
INSTALLED_APPS += [  # noqa: F405
    "allauth.socialaccount.providers.github",
    "allauth.socialaccount.providers.discord",
]

# Social auth providers configuration
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "OAUTH_PKCE_ENABLED": True,
    },
    "github": {
        "SCOPE": [
            "user:email",
        ],
    },
}

# Disable auto-login for production
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Account settings for social auth
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "mandatory"

# Logging configuration for production
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "lexiflux": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
