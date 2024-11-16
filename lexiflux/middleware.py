"""Middleware for handling transactions in Django views."""

import logging
from typing import Any

from django.contrib.auth import authenticate, login
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from lexiflux.lexiflux_settings import settings


logger = logging.getLogger(__name__)


class AutoLoginMiddleware:  # pylint: disable=too-few-public-methods
    """Middleware for auto-login."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        if not request.user.is_authenticated and settings.lexiflux.skip_auth:
            if user := authenticate(
                username=settings.lexiflux.default_user_name,
                password=settings.lexiflux.default_user_password,
            ):
                login(request, user)
        return self.get_response(request)


class JSONPermissionDeniedMiddleware:
    """Middleware to format responses in case of PermissionDenied exceptions."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        return self.get_response(request)

    def process_exception(self, request: Any, exception: Any) -> Any:
        """Process exception."""
        if isinstance(exception, PermissionDenied):
            return JsonResponse({"error": str(exception) or "Permission denied"}, status=403)
        return None
