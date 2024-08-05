"""Settings for Lexiflux."""

from dataclasses import dataclass
import os
import warnings
from typing import Any
from django.conf import settings as django_settings


SINGLE_USER_ENV = "LEXIFLUX_SINGLE_USER"
SKIP_AUTH_ENV = "LEXIFLUX_SKIP_AUTH"
ENV_SETTINGS_ENV = "LEXIFLUX_ENV_SETTINGS"


@dataclass
class EnvironmentVars:
    """Environment variables for Lexiflux."""

    is_single_user: bool
    skip_auth: bool
    env_settings: bool  # if user can edit environment vars, basically for local run without Docker

    @classmethod
    def from_environment(cls) -> "EnvironmentVars":
        """Create an instance from environment variables."""
        is_single_user = os.environ.get(SINGLE_USER_ENV, "").lower() == "true"
        skip_auth = os.environ.get(SKIP_AUTH_ENV, "").lower() == "true"

        return cls(
            is_single_user=is_single_user,
            skip_auth=skip_auth,
            env_settings=os.environ.get(ENV_SETTINGS_ENV, "").lower() == "true",
        )

    def validate(self) -> None:
        """Validate the environment variables.

        Raises exception if env vars are not consistent.
        """
        if self.skip_auth and not self.is_single_user:
            raise ValueError(
                "`LEXIFLUX_SKIP_AUTH` should not be used in multi-user environment "
                "(`LEXIFLUX_SINGLE_USER` is not `true`)!"
            )

        if self.skip_auth:
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
