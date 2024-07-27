"""Middleware for handling transactions in Django views."""

import logging
from typing import Any

from django.db import transaction
from django.http import JsonResponse
from django.db.utils import DatabaseError

logger = logging.getLogger(__name__)


class TransactionMiddleware:
    """Middleware for handling transactions in Django views."""

    def __init__(self, get_response: Any) -> None:
        """`Initialize the middleware with the get_response callable."""
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        """Process the request and response."""
        try:
            with transaction.atomic():
                response = self.get_response(request)
                if transaction.get_connection().needs_rollback:
                    transaction.set_rollback(True)
                    raise DatabaseError("Transaction needs rollback")
                return response
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("An error occurred during the request")
            if transaction.get_connection().in_atomic_block:
                transaction.set_rollback(True)
            return self.handle_exception(e)

    def handle_exception(self, exc: Exception) -> JsonResponse:
        """Handle exceptions that occur during the request."""
        if isinstance(exc, DatabaseError):
            return JsonResponse(
                {"status": "error", "message": "A database error occurred"}, status=500
            )
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)
