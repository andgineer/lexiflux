"""Middleware for handling transactions in Django views."""

import logging
from typing import Any

from django.contrib.auth import authenticate, login
from lexiflux.lexiflux_settings import settings
from lexiflux.management.commands.startup import DEFAULT_USER_NAME, DEFAULT_USER_PASSWORD


logger = logging.getLogger(__name__)


class AutoLoginMiddleware:  # pylint: disable=too-few-public-methods
    """Middleware for auto-login."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        if not request.user.is_authenticated and settings.env.is_single_user:
            if user := authenticate(username=DEFAULT_USER_NAME, password=DEFAULT_USER_PASSWORD):
                login(request, user)
        return self.get_response(request)
