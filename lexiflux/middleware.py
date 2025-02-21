"""Middleware for handling transactions in Django views."""

import logging
from typing import Any

from django.contrib.auth import authenticate, login
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import HttpResponseNotAllowed, JsonResponse

from lexiflux.lexiflux_settings import settings

logger = logging.getLogger(__name__)


class AutoLoginMiddleware:  # pylint: disable=too-few-public-methods
    """Middleware for auto-login."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        if not request.user.is_authenticated and settings.lexiflux.skip_auth:  # noqa: SIM102
            if user := authenticate(
                username=settings.lexiflux.default_user_name,
                password=settings.lexiflux.default_user_password,
            ):
                login(request, user)
        return self.get_response(request)


class ExceptionJSONResponseMiddleware:
    """Middleware to format responses in case of PermissionDenied exceptions."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        response = self.get_response(request)
        # Convert HttpResponseNotAllowed to JSON format
        if isinstance(response, HttpResponseNotAllowed):
            allowed_methods = response.headers.get("Allow", "")
            return JsonResponse(
                {
                    "error": (
                        f"Method {request.method} not allowed. Allowed methods: {allowed_methods}"
                    ),
                    "details": [request.path],
                },
                status=405,
            )
        return response

    def process_exception(self, request: Any, exception: Any) -> Any:  # noqa: ARG002
        """Process exceptions and return JSON response."""
        logger.exception("Exception: %s", exception)

        if isinstance(exception.args, tuple) and len(exception.args) > 0:
            # Convert WSGIRequest objects to their URL path and keep other args as strings
            exception_args = [
                arg.path if str(type(arg)).endswith("WSGIRequest") else str(arg)
                for arg in exception.args[:-1]
            ]
            error_message = exception.args[-1]
        else:
            error_message = str(exception)
            exception_args = [str(exception.args)]
        if isinstance(exception, PermissionDenied):
            return JsonResponse(
                {"error": error_message or "Permission denied", "details": exception_args},
                status=403,
            )
        if isinstance(exception, (ValueError, ObjectDoesNotExist)):
            return JsonResponse(
                {"error": error_message or "Bad request", "details": exception_args},
                status=400,
            )
        return JsonResponse(
            {"error": error_message or "Internal server error", "details": exception_args},
            status=500,
        )
