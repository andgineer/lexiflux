"""Custom decorators for LexiFlux."""

from functools import wraps
from typing import Callable, Any
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from lexiflux.lexiflux_settings import settings
from lexiflux.management.commands.startup import DEFAULT_USER_NAME


def get_default_user() -> Any:
    """Get the default user."""
    return get_user_model().objects.get_or_create(username=DEFAULT_USER_NAME)[0]


def smart_login_required(
    view_func: Callable[[HttpRequest, Any], HttpResponse],
) -> Callable[[HttpRequest, Any], HttpResponse]:
    """Login required decorator that does not require login if not in cloud."""

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if settings.env.skip_auth:
            if isinstance(request.user, AnonymousUser):
                request.user = get_default_user()
            return view_func(request, *args, **kwargs)
        return login_required(view_func)(request, *args, **kwargs)

    return wrapper
