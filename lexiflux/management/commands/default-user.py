"""Startup tasks for LexiFlux."""  # pylint: disable=invalid-name

import contextlib
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lexiflux.lexiflux_settings import settings


class Command(BaseCommand):  # type: ignore
    """Command for performing startup tasks."""

    help = "Creates default user for auto-login."

    def handle(self, *args: Any, **options: Any) -> None:
        user_class = get_user_model()

        if settings.env.skip_auth:  # todo: check we are not in a cloud
            username = settings.env.default_user_name
            email = settings.env.default_user_email
            password = settings.env.default_user_password

            if not user_class.objects.filter(username=username).exists():
                user_class.objects.create_user(username=username, email=email, password=password)
                self.stdout.write(f"Created default user: {username}")
            else:
                self.stdout.write("Default user already exists")
        else:
            # if in auth mode the default user has the default password, raise an error
            with contextlib.suppress(ObjectDoesNotExist):
                user = user_class.objects.get(username=settings.env.default_user_name)
                if user.check_password(settings.env.default_user_password):
                    raise ValueError(
                        "Default user was created in `LEXIFLUX_SKIP_AUTH` mode. "
                        "We are in multi-user environment and it's not safe "
                        "to have a user with the default password. "
                        "Please change the password for the default user "
                        f"`{settings.env.default_user_name}` or delete it."
                    )
        self.stdout.write("Default user created")
