"""Settings for Lexiflux."""

import contextlib
import logging
import os
import sys
import warnings
from dataclasses import dataclass
from typing import Any

import django.db.utils
import requests
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger()

SKIP_AUTH_ENV = "LEXIFLUX_SKIP_AUTH"
UI_SETTINGS_ONLY_ENV = "LEXIFLUX_UI_SETTINGS_ONLY"
ENV_NAME_ENV = "LEXIFLUX_ENV_NAME"

AUTOLOGIN_USER_NAME = "lexiflux"
AUTOLOGIN_USER_PASSWORD = "lexiflux"  # noqa: S105
AUTOLOGIN_USER_EMAIL = "lexiflux@example.com"


def is_running_in_cloud() -> bool:
    """Check if the code is running in a cloud environment."""
    cloud_env_vars = [
        "AWS_EXECUTION_ENV",
        "GAE_ENV",
        "GCP_PROJECT",
        "WEBSITE_INSTANCE_ID",
        "WEBSITE_SITE_NAME",
    ]
    return any(var in os.environ for var in cloud_env_vars) or is_running_in_aws()


def is_running_in_aws() -> bool:
    """Check if the code is running in AWS."""
    try:
        response = requests.get("http://169.254.169.254/latest/meta-data/", timeout=0.1)
        return response.status_code == 200  # noqa: PLR2004
    except requests.exceptions.RequestException:
        return False


@dataclass
class EnvironmentVars:
    """Environment variables for Lexiflux."""

    env_name: str
    skip_auth: bool
    ui_settings_only: (  # user cannot edit environment vars
        bool
    )

    default_user_name: str
    default_user_password: str
    default_user_email: str

    @classmethod
    def from_environment(cls) -> "EnvironmentVars":
        """Create an instance from environment variables."""
        skip_auth = os.environ.get(SKIP_AUTH_ENV, "").lower() == "true"
        if is_running_in_cloud():
            skip_auth = False

            warnings.warn(
                "(!) Authentication is NOT skipped - cloud environment detected.",
                RuntimeWarning,
                stacklevel=2,
            )
        if skip_auth:
            warnings.warn(
                "(!) Authentication is being skipped (`LEXIFLUX_SKIP_AUTH` set to True) "
                "but this is not recommended in a cloud environment.",
                RuntimeWarning,
                stacklevel=2,
            )

        return cls(
            env_name=os.environ.get(ENV_NAME_ENV, "local"),
            skip_auth=skip_auth,
            ui_settings_only=os.environ.get(UI_SETTINGS_ONLY_ENV, "").lower() == "true",
            default_user_name=AUTOLOGIN_USER_NAME,
            default_user_password=AUTOLOGIN_USER_PASSWORD,
            default_user_email=AUTOLOGIN_USER_EMAIL,
        )

    def is_running_migration(self) -> bool:
        """Check if the code is running in a migration."""
        return "migrate" in sys.argv or self.env_name.lower() == "test"

    def validate(self) -> None:
        """Validate the environment variables.

        Raises exception if env vars are not consistent.
        """
        try:
            if not self.skip_auth:
                with contextlib.suppress(ObjectDoesNotExist):
                    user = get_user_model().objects.get(username=AUTOLOGIN_USER_NAME)
                    if user.check_password(AUTOLOGIN_USER_PASSWORD):
                        raise ValueError(
                            "We are in multi-user environment but the auto-login user "
                            "with hard-coded password exists. "
                            "Please change the password for the user "
                            f"`{AUTOLOGIN_USER_NAME}` or delete it.",
                        )
        except django.db.utils.OperationalError as e:
            if not ("no such table: lexiflux_customuser" in str(e) and self.is_running_migration()):
                raise


class LexifluxSettings:  # pylint: disable=too-few-public-methods
    """Settings for Lexiflux."""

    def __init__(self) -> None:
        self.lexiflux = EnvironmentVars.from_environment()

    def __getattr__(self, name: str) -> Any:
        return getattr(django_settings, name)


settings = LexifluxSettings()
