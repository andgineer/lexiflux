"""Startup tasks for LexiFlux."""

import contextlib
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lexiflux.lexiflux_settings import settings


DEFAULT_USER_NAME = "lexiflux"
DEFAULT_USER_PASSWORD = "lexiflux"
DEFAULT_USER_EMAIL = "lexiflux@example.com"


class Command(BaseCommand):  # type: ignore
    """Command for performing startup tasks."""

    help = "Performs startup tasks"

    def handle(self, *args: Any, **options: Any) -> None:
        user_class = get_user_model()

        if settings.env.skip_auth:
            username = DEFAULT_USER_NAME
            email = DEFAULT_USER_EMAIL
            password = DEFAULT_USER_PASSWORD

            if not user_class.objects.filter(username=username).exists():
                user_class.objects.create_user(username=username, email=email, password=password)
                self.stdout.write(f"Created default user: {username}")
            else:
                self.stdout.write("Default user already exists")
        else:
            # if in auth mode the default user has the default password, raise an error
            with contextlib.suppress(ObjectDoesNotExist):
                user = user_class.objects.get(username=DEFAULT_USER_NAME)
                if user.check_password(DEFAULT_USER_PASSWORD):
                    raise ValueError(
                        "Default user was created in `LEXIFLUX_SKIP_AUTH` mode. "
                        "We are in multi-user environment and it's not safe "
                        "to have a user with the default password. "
                        "Please change the password for the default user "
                        f"`{DEFAULT_USER_NAME}` or delete it."
                    )
        self.stdout.write("Startup tasks completed")
