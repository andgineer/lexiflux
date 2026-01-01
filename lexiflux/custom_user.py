"""Type-safe helpers for working with CustomUser model."""

from typing import TYPE_CHECKING, cast

from django.http import HttpRequest

if TYPE_CHECKING:
    from lexiflux.models import CustomUser


def get_custom_user(request: HttpRequest) -> "CustomUser":
    """Type-safe helper to get CustomUser from request after authentication.

    Use this after @smart_login_required or @login_required decorators
    to tell the type checker that request.user is definitely CustomUser.
    """
    return cast("CustomUser", request.user)


def get_custom_user_model() -> type["CustomUser"]:
    """Type-safe helper to get CustomUser model class.

    Use this instead of get_user_model() when you need to access
    CustomUser-specific attributes to tell the type checker
    that the model is CustomUser, not AbstractBaseUser.
    """
    from lexiflux.models import CustomUser  # noqa: PLC0415

    return CustomUser
