"""Django Custom User Backend"""

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest


class CustomUserBackend(ModelBackend):  # type: ignore
    """Custom user backend for authentication."""

    def authenticate(
        self,
        request: HttpRequest | None,  # noqa: ARG002
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,  # noqa: ARG002
    ) -> AbstractBaseUser | None:
        """Authenticate a user."""
        if not password:
            return None
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=username)
            if user.check_password(password) and (user.is_approved or user.is_superuser):
                return user
        except user_model.DoesNotExist:
            # Timing attack protection: hash password even for non-existent users
            # to ensure consistent response time and prevent username enumeration
            # the user_model will be garbage collected without saving to DB
            user_model().set_password(password)
        return None
