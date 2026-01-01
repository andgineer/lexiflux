"""Custom decorators for LexiFlux."""

import logging
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar, cast

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse

from lexiflux.lexiflux_settings import settings

if TYPE_CHECKING:
    from lexiflux.models import CustomUser

logger = logging.getLogger(__name__)

# TypeVar for preserving function signatures in decorators
_ViewFunc = TypeVar("_ViewFunc", bound=Callable[..., HttpResponse])


def get_custom_user(request: HttpRequest) -> "CustomUser":
    """Type-safe helper to get CustomUser from request after authentication.

    Use this after @smart_login_required or @login_required decorators
    to tell the type checker that request.user is definitely CustomUser.
    """
    return cast("CustomUser", request.user)


def get_default_user() -> Any:
    """Get the default user."""
    user, created = get_user_model().objects.get_or_create(
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


def smart_login_required(view_func: _ViewFunc) -> _ViewFunc:
    """Login required decorator that does not require login if not in cloud."""

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if settings.lexiflux.skip_auth:
            if isinstance(request.user, AnonymousUser):
                request.user = get_default_user()
            return view_func(request, *args, **kwargs)
        return login_required(view_func)(request, *args, **kwargs)

    return wrapper  # type: ignore[return-value]
