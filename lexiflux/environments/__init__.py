"""
Environment auto-detection for Lexiflux Django settings.

This module automatically loads the appropriate settings based on environment variables.
Supports: local, docker, koyeb
"""

import os


def get_environment() -> str:
    """
    Detect the current environment based on environment variables.

    Returns:
        str: Environment name ('local', 'docker', 'koyeb')

    Raises:
        ValueError: If no valid environment is detected
    """
    # Check for explicit environment setting
    env = os.environ.get("LEXIFLUX_ENV", "").lower()
    if env in ["local", "docker", "koyeb"]:
        return env

    # Auto-detect based on environment indicators
    if os.environ.get("KOYEB_DEPLOYMENT_ID"):
        return "koyeb"

    if os.environ.get("LEXIFLUX_UI_SETTINGS_ONLY") == "true":
        return "docker"

    # NO FALLBACK - require explicit configuration
    raise ValueError(
        "No valid environment detected. Please set LEXIFLUX_ENV to one of:"
        " 'local', 'docker', 'koyeb'. "
        "This is required for security - no default environment is allowed.",
    )


# Auto-import the appropriate environment settings
current_env = get_environment()

if current_env == "local":
    from .local import *  # noqa: F401,F403
elif current_env == "docker":
    from .docker import *  # noqa: F401,F403
elif current_env == "koyeb":
    from .koyeb import *  # noqa: F401,F403
else:
    # This should never happen due to get_environment() validation
    raise ValueError(f"Unknown environment: {current_env}")

# Make environment info available
LEXIFLUX_ENVIRONMENT = current_env
