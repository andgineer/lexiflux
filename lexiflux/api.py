"""API utilities."""

import re
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.http import HttpRequest, JsonResponse
from pydantic import BaseModel, ValidationError


def to_kebab_case(string: str) -> str:
    """Convert snake_case to kebab-case."""
    return re.sub(r"_", "-", string)


class ViewGetParamsModel(BaseModel):  # pylint: disable=too-few-public-methods
    """Base class for GET params models."""

    class Config:  # pylint: disable=too-few-public-methods
        """Pydantic configuration."""

        alias_generator = to_kebab_case
        populate_by_name = True


def get_params(schema: type[BaseModel]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to validate GET params using Pydantic models."""

    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
            try:
                # Convert QueryDict to regular dict to use parse_obj, ensuring single values
                data: dict[str, Any] = {key: request.GET.get(key) for key in request.GET}
                params = schema.parse_obj(data)
                return view_func(request, params, *args, **kwargs)
            except ValidationError as e:
                print("GET params validation error", e.errors())
                return JsonResponse({"error": e.errors()}, status=400)

        return _wrapped_view

    return decorator
