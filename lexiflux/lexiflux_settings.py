"""Settings for Lexiflux."""

import contextlib
from dataclasses import dataclass
import os
import warnings
from typing import Any
import requests
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

SKIP_AUTH_ENV = "LEXIFLUX_SKIP_AUTH"
UI_SETTINGS_ONLY_ENV = "LEXIFLUX_UI_SETTINGS_ONLY"

AUTOLOGIN_USER_NAME = "lexiflux"
AUTOLOGIN_USER_PASSWORD = "lexiflux"
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
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


@dataclass
class EnvironmentVars:
    """Environment variables for Lexiflux."""

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
        if skip_auth:
            if is_running_in_cloud():
                skip_auth = False
                warnings.warn(
                    "(!) Authentication is NOT skipped - cloud environment detected.",
                    RuntimeWarning,
                )
            warnings.warn(
                "(!) Authentication is being skipped (`LEXIFLUX_SKIP_AUTH` set to True) "
                "but this is not recommended in a cloud environment.",
                RuntimeWarning,
            )
        if not skip_auth:
            with contextlib.suppress(ObjectDoesNotExist):
                user = get_user_model().objects.get(username=AUTOLOGIN_USER_NAME)
                if user.check_password(AUTOLOGIN_USER_PASSWORD):
                    raise ValueError(
                        "We are in multi-user environment but the auto-login user "
                        "with hard-coded password exists. "
                        "Please change the password for the user "
                        f"`{AUTOLOGIN_USER_NAME}` or delete it."
                    )

        return cls(
            skip_auth=skip_auth,
            ui_settings_only=os.environ.get(UI_SETTINGS_ONLY_ENV, "").lower() == "true",
            default_user_name=AUTOLOGIN_USER_NAME,
            default_user_password=AUTOLOGIN_USER_PASSWORD,
            default_user_email=AUTOLOGIN_USER_EMAIL,
        )

    def validate(self) -> None:
        """Validate the environment variables.

        Raises exception if env vars are not consistent.
        """


class LexifluxSettings:  # pylint: disable=too-few-public-methods
    """Settings for Lexiflux."""

    def __init__(self) -> None:
        self.env = EnvironmentVars.from_environment()

    def __getattr__(self, name: str) -> Any:
        return getattr(django_settings, name)


settings = LexifluxSettings()
