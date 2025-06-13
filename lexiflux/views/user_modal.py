"""User modal view."""

import logging

from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods

from lexiflux.decorators import smart_login_required
from lexiflux.models import Language, LanguagePreferences

logger = logging.getLogger()


@smart_login_required
@require_http_methods(["GET", "POST"])  # type: ignore
def user_modal(request: HttpRequest) -> HttpResponse:
    """User modal view."""
    logger.info(f"User: {request.user.username} (ID: {request.user.id})")
    logger.info(f"User.language: {request.user.language}")
    logger.info(f"User.default_language_preferences: {request.user.default_language_preferences}")

    existing_prefs = LanguagePreferences.objects.filter(user=request.user)
    logger.info(f"Existing language preferences count: {existing_prefs.count()}")
    for pref in existing_prefs:
        logger.info(f"  - {pref.language} -> {pref.user_language} (ID: {pref.id})")

    if request.method == "POST":
        language_id = request.POST.get("language")
        # when the checkbox is disable it's not included in the POST data, thus the hack:
        # we know that iа user has no language set, we should update all preferences
        update_all = (
            request.POST.get("update_all_preferences") == "on" or request.user.language is None
        )

        logger.info(f"POST user_modal - language_id: {language_id}")
        logger.info(
            f"POST user_modal - update_all_preferences: "
            f"{request.POST.get('update_all_preferences')}",
        )
        logger.info(f"Computed update_all: {update_all}")
        logger.info(f"User.language is None: {request.user.language is None}")

        if language_id:
            new_language = Language.objects.get(google_code=language_id)
            logger.info(f"Found language: {new_language} ({new_language.google_code})")

            with transaction.atomic():
                old_language = request.user.language
                logger.info(f"Old user language: {old_language}")

                request.user.language = new_language
                request.user.save()

                if update_all:
                    logger.info("Starting update_all prefs...")
                    prefs_to_update = LanguagePreferences.objects.filter(user=request.user)
                    logger.info(f"Preferences to update: {prefs_to_update.count()}")

                    for pref in prefs_to_update:
                        logger.info(f"  Before update - {pref.language} -> {pref.user_language}")

                    updated_count = LanguagePreferences.objects.filter(user=request.user).update(
                        user_language=request.user.language,
                    )
                    logger.info(f"Updated {updated_count} language preferences")

                    updated_prefs = LanguagePreferences.objects.filter(user=request.user)
                    for pref in updated_prefs:
                        logger.info(f"  After update - {pref.language} -> {pref.user_language}")

                    if request.user.default_language_preferences:
                        logger.info(
                            f"Refreshing default_language_preferences (ID: "
                            f"{request.user.default_language_preferences.id})",
                        )
                        request.user.default_language_preferences.refresh_from_db()
                        logger.info(
                            f"Default prefs after refresh: "
                            f"{request.user.default_language_preferences.language} "
                            f"-> {request.user.default_language_preferences.user_language}",
                        )
                    else:
                        logger.warning("User has no default_language_preferences!")
            logger.info("=== USER MODAL DEBUG END (SUCCESS) ===")
            return HttpResponse(headers={"HX-Refresh": "true"})
        return HttpResponse(status=400)

    context = {"languages": Language.objects.all().order_by("name")}
    return TemplateResponse(request, "partials/user_modal.html", context)
