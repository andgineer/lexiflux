"""Middleware for handling transactions in Django views."""

import logging
from typing import Any

from django.contrib.auth import authenticate, login
from lexiflux.lexiflux_settings import settings


logger = logging.getLogger(__name__)


class AutoLoginMiddleware:  # pylint: disable=too-few-public-methods
    """Middleware for auto-login."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        if not request.user.is_authenticated and settings.env.skip_auth:
            if user := authenticate(
                username=settings.env.default_user_name,
                password=settings.env.default_user_password,
            ):
                login(request, user)
        return self.get_response(request)
