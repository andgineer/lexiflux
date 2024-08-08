"""Django Custom User Backend"""

from typing import Optional, Any

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest


class CustomUserBackend(ModelBackend):  # type: ignore
    """Custom user backend for authentication."""

    def authenticate(
        self,
        request: Optional[HttpRequest],
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[AbstractBaseUser]:
        """Authenticate a user."""
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=username)
            if user.check_password(password) and (user.is_approved or user.is_superuser):
                return user
        except user_model.DoesNotExist:
            user_model().set_password(password)
        return None
