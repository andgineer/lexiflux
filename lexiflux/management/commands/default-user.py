"""Creates fixed user for auto-login."""  # pylint: disable=invalid-name

import contextlib
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from lexiflux.decorators import get_default_user
from lexiflux.lexiflux_settings import settings


class Command(BaseCommand):  # type: ignore
    """Command for performing startup tasks."""

    help = "Creates fixed user for auto-login."

    def handle(self, *args: Any, **options: Any) -> None:
        user_class = get_user_model()

        if settings.lexiflux.skip_auth:
            if not user_class.objects.filter(
                username=settings.lexiflux.default_user_name
            ).exists():
                user = get_default_user()
                self.stdout.write(f"Created default user: {user.email}")
                self.stdout.write(
                    "(!) Warning: the user has hard-coded password for auto-login. "
                    "Do not use in multi-user environment."
                )
            else:
                with contextlib.suppress(ObjectDoesNotExist):
                    user = user_class.objects.get(username=settings.lexiflux.default_user_name)
                    if user.check_password(settings.lexiflux.default_user_password):
                        self.stdout.write("Default user already exists")
                    else:
                        self.stdout.write(
                            "Default user exists but has a different password. "
                            "For auto-login you should delete it and re-create."
                        )
        else:
            # if in auth mode the default user has the default password, raise an error
            with contextlib.suppress(ObjectDoesNotExist):
                user = user_class.objects.get(username=settings.lexiflux.default_user_name)
                if user.check_password(settings.lexiflux.default_user_password):
                    raise ValueError(
                        "We are in multi-user environment but the auto-login user "
                        "with hard-coded password exists. "
                        "Please change the password for the user "
                        f"`{settings.lexiflux.default_user_name}` or delete it."
                    )
            self.stdout.write(
                "Authentication is not skipped (LEXIFLUX_SKIP_AUTH is not true)."
                "Auto-login user is not created."
            )
