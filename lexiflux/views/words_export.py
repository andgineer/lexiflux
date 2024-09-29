"""Views for exporting words to Anki or other cards learning apps."""

import json
import logging
from typing import Any

from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Max

from lexiflux.decorators import smart_login_required
from lexiflux.models import Language, LanguageGroup, TranslationHistory, WordsExport


logger = logging.getLogger(__name__)


@smart_login_required  # type: ignore
def words_export(request: HttpRequest) -> HttpResponse:
    """Render the words export page."""
    return render(request, "words-export.html")


@smart_login_required
@require_http_methods(["GET"])  # type: ignore
def words_export_options(request: HttpRequest) -> HttpResponse:
    """Get available languages and language groups for export."""
    user = request.user

    # Get languages with translations
    languages = (
        Language.objects.filter(translation_history__user=user)
        .distinct()
        .values("google_code", "name")
    )

    # Get language groups with translations
    language_groups = (
        LanguageGroup.objects.filter(languages__translation_history__user=user)
        .distinct()
        .values("id", "name")
    )

    return JsonResponse({"languages": list(languages), "language_groups": list(language_groups)})


@smart_login_required
@require_http_methods(["GET"])  # type: ignore
def last_export_datetime(request: HttpRequest) -> HttpResponse:
    """Get the last export datetime for a given language or language group."""
    try:
        language_id = request.GET.get("language")
        user = request.user

        if not language_id:
            return JsonResponse({"error": "Language parameter is required"}, status=400)

        last_export = None
        if language_id.isdigit():  # It's a language group
            group = LanguageGroup.objects.get(id=language_id)
            last_export = WordsExport.objects.filter(
                user=user, language__in=group.languages.all()
            ).aggregate(Max("export_datetime"))["export_datetime__max"]
        else:  # It's a language
            language = Language.objects.get(google_code=language_id)
            last_export = (
                WordsExport.objects.filter(user=user, language=language)
                .order_by("-export_datetime")
                .first()
            )
        if last_export is None:
            # set to the beginning of the year just to simplify editing the date in the frontend
            last_export = timezone.datetime(timezone.now().year, 1, 1)
        logger.info(f"For language {language_id} last export datetime: {last_export}")
        return JsonResponse(
            {"last_export_datetime": last_export.isoformat() if last_export else None}
        )
    except LanguageGroup.DoesNotExist:
        return JsonResponse({"error": "Language group not found"}, status=404)
    except Language.DoesNotExist:
        return JsonResponse({"error": "Language not found"}, status=404)
    except ValueError:
        return JsonResponse({"error": "Invalid language or language group ID"}, status=400)
    except Exception as e:  # pylint: disable=broad-except
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)


@smart_login_required
@require_http_methods(["POST"])  # type: ignore
def export_words(request: HttpRequest) -> HttpResponse:
    """Export words for the given language or language group."""
    data = json.loads(request.body)
    language_id = data.get("language")
    export_format = "CSV"
    min_datetime = timezone.datetime.fromisoformat(data.get("min_datetime"))
    user = request.user

    try:
        if language_id.isdigit():  # It's a language group
            group = LanguageGroup.objects.get(id=language_id)
            terms = TranslationHistory.objects.filter(
                user=user, source_language__in=group.languages.all(), last_lookup__gte=min_datetime
            )
            language = (
                group.languages.first()
            )  # Use the first language of the group for the export record
        else:  # It's a language
            language = Language.objects.get(google_code=language_id)
            terms = TranslationHistory.objects.filter(
                user=user, source_language=language, last_lookup__gte=min_datetime
            )

        words_exported = export_words_to_format(language, export_format, terms)

        WordsExport.objects.create(
            user=user,
            language=language,
            word_count=words_exported,
            details={"format": export_format},
        )

        return JsonResponse({"status": "success", "exported_words": words_exported})
    except Exception as e:  # pylint: disable=broad-except
        return JsonResponse({"status": "error", "error": str(e)})


def export_words_to_format(language: Language, export_format: str, terms: Any) -> int:  # pylint: disable=unused-argument
    """Process translations and return export data."""
    # todo: implement
    return len(terms)
