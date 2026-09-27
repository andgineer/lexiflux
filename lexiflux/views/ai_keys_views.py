"""Views for the AI keys page, where users set their own API keys."""

import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.debug import sensitive_variables
from django.views.decorators.http import require_http_methods

from lexiflux.auth import smart_login_required
from lexiflux.custom_user import get_custom_user
from lexiflux.language.ai_keys import ai_keys, key_rows
from lexiflux.language.broker import refresh_keys
from lexiflux.language.key_store import clear_own_key, save_own_key


@smart_login_required  # type: ignore
def ai_keys_page(request: HttpRequest) -> HttpResponse:
    user = get_custom_user(request)
    return render(request, "ai-keys.html", {"keys": key_rows(user.id)})


@smart_login_required
@require_http_methods(["POST", "DELETE"])  # type: ignore
@sensitive_variables("data", "value")
def ai_key_api(request: HttpRequest, ref: str) -> JsonResponse:
    user = get_custom_user(request)
    if ref not in {key.ref for key in ai_keys()}:
        return JsonResponse({"error": f"Unknown key {ref}"}, status=404)
    if request.method == "DELETE":
        clear_own_key(user, ref)
    else:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "The request is not JSON"}, status=400)
        value = data.get("key") if isinstance(data, dict) else None
        value = value.strip() if isinstance(value, str) else ""
        if not value:
            return JsonResponse({"error": "Enter a key to save"}, status=400)
        save_own_key(user, ref, value)
    refresh_keys()
    (row,) = key_rows(user.id, {ref})
    return JsonResponse({"key": row})
