"""Authentication backend, decorators, and helpers for LexiFlux."""

import logging
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse

from lexiflux.custom_user import get_custom_user_model
from lexiflux.lexiflux_settings import settings

if TYPE_CHECKING:
    from lexiflux.models import CustomUser

logger = logging.getLogger(__name__)


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
        user_model = get_custom_user_model()
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


def get_default_user() -> "CustomUser":
    """Get the default user for auto-login in development."""
    user_model = get_custom_user_model()
    user, created = user_model.objects.get_or_create(
        username=settings.lexiflux.default_user_name,
        defaults={
            "email": settings.lexiflux.default_user_email,
            "is_approved": True,
            "premium": True,
            "password": settings.lexiflux.default_user_password,
        },
    )
    if created:
        logger.info("Created default user: %s", user.email)
    return user


def smart_login_required(view_func: object) -> Callable[..., HttpResponse]:
    """Login required decorator that does not require login if not in cloud."""
    # Accept object type to handle TypeVars from stacked decorators (e.g., @require_GET)
    if not callable(view_func):
        raise TypeError(f"Expected callable, got {type(view_func)}")

    @wraps(view_func)  # type: ignore[arg-type]
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if settings.lexiflux.skip_auth:
            if isinstance(request.user, AnonymousUser):
                request.user = get_default_user()
            return view_func(request, *args, **kwargs)  # type: ignore[operator]
        return login_required(view_func)(request, *args, **kwargs)  # type: ignore[arg-type,operator]

    return wrapper
