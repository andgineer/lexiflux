"""User modal view."""

import logging

from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods

from lexiflux.decorators import get_custom_user, smart_login_required
from lexiflux.models import Language, LanguagePreferences

logger = logging.getLogger()


@smart_login_required
@require_http_methods(["GET", "POST"])  # type: ignore
def user_modal(request: HttpRequest) -> HttpResponse:
    """User modal view."""
    user = get_custom_user(request)
    existing_prefs = LanguagePreferences.objects.filter(user=user)
    for pref in existing_prefs:
        logger.info(f"  - {pref.language} -> {pref.user_language} (ID: {pref.id})")

    if request.method == "POST":
        language_id = request.POST.get("language")
        # when the checkbox is disable it's not included in the POST data, thus the hack:
        # we know that iа user has no language set, we should update all preferences
        update_all = request.POST.get("update_all_preferences") == "on" or user.language is None

        if language_id:
            new_language = Language.objects.get(google_code=language_id)
            logger.info(f"New language: {new_language} ({new_language.google_code})")

            old_language = user.language
            logger.info(f"Old user language: {old_language}")

            user.language = new_language
            user.save()

            if update_all:
                LanguagePreferences.objects.filter(user=user).update(
                    user_language=user.language,
                )
                if not user.default_language_preferences:
                    logger.warning("User has no default_language_preferences!")
            return HttpResponse(headers={"HX-Refresh": "true"})
        return HttpResponse(status=400)

    context = {"languages": Language.objects.all().order_by("name")}
    return TemplateResponse(request, "partials/user_modal.html", context)
