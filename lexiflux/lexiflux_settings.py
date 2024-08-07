"""Settings for Lexiflux."""

from dataclasses import dataclass
import os
import warnings
from typing import Any
from django.conf import settings as django_settings
import requests

SKIP_AUTH_ENV = "LEXIFLUX_SKIP_AUTH"
USER_CONTROL_ENV_ENV = "LEXIFLUX_USER_CONTROL_ENV"


def is_running_in_cloud() -> bool:
    """Check if the code is running in a cloud environment."""
    cloud_env_vars = [
        "AWS_EXECUTION_ENV",
        "GAE_ENV",
        "GCP_PROJECT",
        "WEBSITE_INSTANCE_ID",
        "WEBSITE_SITE_NAME",
    ]
    return any(var in os.environ for var in cloud_env_vars)


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
    user_control_env: (  # todo: ui_settings_only
        bool  # if user can edit environment vars, basically for local run without Docker
    )

    default_user_name: str
    default_user_password: str
    default_user_email: str

    @classmethod
    def from_environment(cls) -> "EnvironmentVars":
        """Create an instance from environment variables."""
        skip_auth = os.environ.get(SKIP_AUTH_ENV, "").lower() == "true"

        return cls(
            skip_auth=skip_auth,
            user_control_env=os.environ.get(USER_CONTROL_ENV_ENV, "").lower() == "true",
            default_user_name="lexiflux",
            default_user_password="lexiflux",
            default_user_email="lexiflux@example.com",
        )

    def validate(self) -> None:
        """Validate the environment variables.

        Raises exception if env vars are not consistent.
        """
        if self.skip_auth:
            # todo: if we are in cloud then clear the skip_auth and write explanation
            warnings.warn(
                "(!) Authentication is being skipped (`LEXIFLUX_SKIP_AUTH` set to True).",
                RuntimeWarning,
            )


class LexifluxSettings:  # pylint: disable=too-few-public-methods
    """Settings for Lexiflux."""

    def __init__(self) -> None:
        self.env = EnvironmentVars.from_environment()

    def __getattr__(self, name: str) -> Any:
        return getattr(django_settings, name)


settings = LexifluxSettings()
