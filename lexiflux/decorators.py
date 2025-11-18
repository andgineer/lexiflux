"""Custom decorators for LexiFlux."""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse

from lexiflux.lexiflux_settings import settings

logger = logging.getLogger(__name__)


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


def smart_login_required(
    view_func: Callable[[HttpRequest, Any], HttpResponse],
) -> Callable[[HttpRequest, Any], HttpResponse]:
    """Login required decorator that does not require login if not in cloud."""

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if settings.lexiflux.skip_auth:
            if isinstance(request.user, AnonymousUser):
                request.user = get_default_user()
            return view_func(request, *args, **kwargs)
        return login_required(view_func)(request, *args, **kwargs)

    return wrapper
