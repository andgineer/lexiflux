"""Creates fixed user for auto-login."""  # pylint: disable=invalid-name

import contextlib
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lexiflux.lexiflux_settings import settings


class Command(BaseCommand):  # type: ignore
    """Command for performing startup tasks."""

    help = "Creates fixed user for auto-login."

    def handle(self, *args: Any, **options: Any) -> None:
        user_class = get_user_model()

        if settings.env.skip_auth:
            username = settings.env.default_user_name
            email = settings.env.default_user_email
            password = settings.env.default_user_password

            if not user_class.objects.filter(username=username).exists():
                user = user_class.objects.create_user(
                    username=username, email=email, password=password
                )
                user.is_approved = True
                user.save()
                self.stdout.write(f"Created default user: {username}")
                self.stdout.write(
                    "(!) Warning: the user has hard-coded password for auto-login. "
                    "Do not use in multi-user environment."
                )
            else:
                with contextlib.suppress(ObjectDoesNotExist):
                    user = user_class.objects.get(username=settings.env.default_user_name)
                    if user.check_password(settings.env.default_user_password):
                        self.stdout.write("Default user already exists")
                    else:
                        self.stdout.write(
                            "Default user exists but has a different password. "
                            "For auto-login you should delete it and re-create."
                        )
        else:
            # if in auth mode the default user has the default password, raise an error
            with contextlib.suppress(ObjectDoesNotExist):
                user = user_class.objects.get(username=settings.env.default_user_name)
                if user.check_password(settings.env.default_user_password):
                    raise ValueError(
                        "We are in multi-user environment but the auto-login user "
                        "with hard-coded password exists. "
                        "Please change the password for the user "
                        f"`{settings.env.default_user_name}` or delete it."
                    )
            self.stdout.write(
                "Authentication is not skipped (LEXIFLUX_SKIP_AUTH is not true)."
                "Auto-login user is not created."
            )
