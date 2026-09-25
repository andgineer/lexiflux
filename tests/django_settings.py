# Override ALLOWED_HOSTS to allow all hosts during testing
import os
import tempfile
from pathlib import Path

os.environ.setdefault("LEXIFLUX_ENV", "local")
from lexiflux.environments import *

ALLOWED_HOSTS = ["*"]

# Never the repo's .llmbroker nor the machine-wide llmbroker cache.
LLMBROKER_HOME = Path(tempfile.mkdtemp(prefix="lexiflux-llmbroker-"))
# Also for llmbroker calls made without home=, which fall back to $LLMBROKER_HOME.
os.environ["LLMBROKER_HOME"] = str(LLMBROKER_HOME)

# Never the repo's Wiktionary file; tests that need one build it from fixtures.
WIKTIONARY_DATABASE = Path(tempfile.mkdtemp(prefix="lexiflux-wiktionary-")) / "wiktionary.sqlite3"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {module} {message}",
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
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
