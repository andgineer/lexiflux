"""Views for exporting words to Anki or other cards learning apps."""  # pylint: disable=duplicate-code
# todo: refactor to extract common code for file and AnkiConnect export

import json
import logging
from datetime import datetime
from typing import cast

from django.db.models import Max
from django.http import FileResponse, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import is_naive, make_aware
from django.views.decorators.http import require_http_methods

from lexiflux.anki.anki_connect import export_words_to_anki_connect
from lexiflux.anki.anki_file import export_words_to_anki_file
from lexiflux.anki.csv_file import export_words_to_csv_file
from lexiflux.decorators import smart_login_required
from lexiflux.models import (
    CustomUser,
    Language,
    LanguageGroup,
    LanguagePreferences,
    TranslationHistory,
    WordsExport,
)

logger = logging.getLogger(__name__)


@smart_login_required  # type: ignore
def words_export_page(request: HttpRequest) -> HttpResponse:  # pylint: disable=too-many-locals
    """Render the words export page with all necessary data."""
    user = request.user

    # Check if translation history is empty
    if not TranslationHistory.objects.filter(user=user).exists():
        context = {
            "languages": json.dumps([]),
            "language_groups": json.dumps([]),
            "default_selection": None,
            "last_export_datetime": None,
            "initial_word_count": 0,
            "default_deck_name": "",
            "previous_deck_names": json.dumps([]),
            "last_export_format": "",
        }
        logger.info("No translations found for the user")
        return render(request, "words-export.html", context)

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
        .prefetch_related("languages")
        .values("id", "name")
    )

    # add to languages all languages from the groups
    for group in language_groups:
        group_languages = LanguageGroup.objects.get(id=group["id"]).languages.values(
            "google_code",
            "name",
        )
        for lang in group_languages:
            if lang not in languages:
                languages = list(languages) + [lang]

    # select last used language
    # but if it is not in translation history, use the first language from the history
    language_prefs = LanguagePreferences.get_or_create_language_preferences(
        user,
        user.default_language_preferences.language,
    )
    language_selection = next(
        (
            lang["google_code"]
            for lang in languages
            if lang["google_code"] == language_prefs.language.google_code
        ),
        languages[0]["google_code"],
    )

    # Get the last export datetime for the default selection
    last_export = None
    language = None
    if language_selection:
        language = Language.objects.get(google_code=language_selection)
        last_export = (
            WordsExport.objects.filter(user=user, language=language)
            .order_by("-export_datetime")
            .first()
        )

    if last_export:
        last_export_date = last_export.export_datetime.isoformat()
    else:
        # Set to the beginning of the year if no export exists
        last_export_date = timezone.datetime(timezone.now().year, 1, 1).isoformat()

    # Check if the selected language is part of a language group
    for group in language_groups:
        group_languages = LanguageGroup.objects.get(id=group["id"]).languages.values_list(
            "google_code",
            flat=True,
        )
        if language_selection in group_languages:
            language_selection = group["id"]
            break

    initial_word_count = TranslationHistory.objects.filter(
        user=user,
        source_language=language if language_selection else None,
        last_lookup__gte=timezone.datetime.fromisoformat(last_export_date),
    ).count()

    default_deck_name = WordsExport.get_default_deck_name(user, language)
    previous_deck_names = WordsExport.get_previous_deck_names(user)
    last_export_format = WordsExport.get_last_export_format(user, language)

    context = {
        "languages": json.dumps(list(languages)),
        "language_groups": json.dumps(list(language_groups)),
        "default_selection": language_selection,
        "last_export_datetime": last_export_date,
        "initial_word_count": initial_word_count,
        "default_deck_name": default_deck_name,
        "previous_deck_names": json.dumps(previous_deck_names),
        "last_export_format": last_export_format,
    }

    return render(request, "words-export.html", context)


def get_group_last_export(user: CustomUser, group_id: str) -> datetime | None:
    """Get last export datetime for a language group."""
    group = LanguageGroup.objects.get(id=group_id)
    return WordsExport.objects.filter(
        user=user,
        language__in=group.languages.all(),
    ).aggregate(Max("export_datetime"))["export_datetime__max"]


def get_language_last_export(user: CustomUser, language_code: str) -> datetime | None:
    """Get last export datetime for a single language."""
    language = Language.objects.get(google_code=language_code)
    export = (
        WordsExport.objects.filter(user=user, language=language)
        .order_by("-export_datetime")
        .first()
    )
    return export.export_datetime if export else None


@smart_login_required
@require_http_methods(["GET"])  # type: ignore
def last_export_datetime(request: HttpRequest) -> HttpResponse:
    """Get the last export datetime for a given language or language group."""
    language_id = request.GET.get("language")
    if not language_id:
        return JsonResponse({"error": "Language parameter is required"}, status=400)

    try:
        last_export = (
            get_group_last_export(request.user, language_id)
            if language_id.isdigit()
            else get_language_last_export(request.user, language_id)
        )

        if not last_export:
            last_export = timezone.datetime(timezone.now().year, 1, 1)

        # Cast to datetime since we know it can't be None at this point
        last_export = cast(datetime, last_export)

        logger.info(f"For language {language_id} last export datetime: {last_export}")

        return JsonResponse({"last_export_datetime": last_export.isoformat()})

    except (LanguageGroup.DoesNotExist, Language.DoesNotExist):
        return JsonResponse({"error": "Language not found"}, status=404)
    except ValueError:
        return JsonResponse({"error": "Invalid language or language group ID"}, status=400)
    except Exception as e:  # noqa: BLE001
        logger.exception("Error in last_export_datetime")
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)


@smart_login_required
@require_http_methods(["POST"])  # type: ignore
def export_words(request: HttpRequest) -> HttpResponse:  # pylint: disable=too-many-locals
    """Export words for the given language or language group."""
    data = json.loads(request.body)
    language_id = data.get("language")
    export_method = data.get("export_method")
    min_datetime = timezone.datetime.fromisoformat(data.get("min_datetime"))
    deck_name = data.get("deck_name", "")
    if is_naive(min_datetime):
        min_datetime = make_aware(min_datetime)
    user = request.user

    try:
        if isinstance(language_id, str) and language_id.isdigit():
            group = LanguageGroup.objects.get(id=int(language_id))
            languages = list(group.languages.all())
            terms = TranslationHistory.objects.filter(
                user=user,
                source_language__in=group.languages.all(),
                last_lookup__gte=min_datetime,
            )
            # select last used language if it's in the translation history,
            # else the first language from the group
            language_prefs = LanguagePreferences.get_or_create_language_preferences(
                user,
                user.default_language_preferences.language,
            )
            language = next(
                (
                    lang
                    for lang in languages
                    if lang.google_code == language_prefs.language.google_code
                ),
                languages[0],
            )
        else:
            language = Language.objects.get(google_code=language_id)
            languages = [language]
            terms = TranslationHistory.objects.filter(
                user=user,
                source_language=language,
                last_lookup__gte=min_datetime,
            )

        words_exported = len(terms)

        if export_method == "ankiConnect":
            words_exported = export_words_to_anki_connect(language, terms, deck_name)
            logger.info(f"Words exported for {language.name}: {words_exported} words")
            response_data = {"status": "success", "exported_words": words_exported}
            response = JsonResponse(response_data)
        elif export_method == "ankiFile":
            file, filename = export_words_to_anki_file(language, terms, deck_name)
            response = FileResponse(file, as_attachment=True, filename=filename)
        elif export_method == "csvFile":
            file, filename = export_words_to_csv_file(language, terms)
            response = FileResponse(
                file,
                as_attachment=True,
                filename=filename,
                content_type="text/csv",
            )
        else:
            raise ValueError("Invalid export method")

        for lang in languages:
            WordsExport.objects.create(
                user=user,
                language=lang,
                word_count=words_exported,
                details={"format": export_method},
                deck_name=deck_name,
                export_format=export_method,
            )

        logger.info(
            f"Words exported for {language.name}: {words_exported} words using {export_method}",
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Error exporting words")
        return JsonResponse({"status": "error", "error": str(e)})
    else:
        return response


@smart_login_required
@require_http_methods(["GET"])  # type: ignore
def word_count(request: HttpRequest) -> HttpResponse:
    """Get the number of words for a given language or language group."""
    try:
        language_id = request.GET.get("language")
        min_datetime = request.GET.get("min_datetime")
        user = request.user

        if not language_id or not min_datetime:
            return JsonResponse(
                {"error": "Language and min_datetime parameters are required"},
                status=400,
            )

        min_datetime = timezone.datetime.fromisoformat(min_datetime)
        if is_naive(min_datetime):
            min_datetime = make_aware(min_datetime)

        if language_id.isdigit():  # It's a language group
            group = LanguageGroup.objects.get(id=int(language_id))
            exported_words_count = TranslationHistory.objects.filter(
                user=user,
                source_language__in=group.languages.all(),
                first_lookup__gte=min_datetime,
            ).count()
        else:  # It's a language
            language = Language.objects.get(google_code=language_id)
            exported_words_count = TranslationHistory.objects.filter(
                user=user,
                source_language=language,
                first_lookup__gte=min_datetime,
            ).count()

        return JsonResponse({"word_count": exported_words_count})

    except (LanguageGroup.DoesNotExist, Language.DoesNotExist):
        return JsonResponse({"error": "Language or language group not found"}, status=404)
    except ValueError:
        return JsonResponse({"error": "Invalid language ID or datetime format"}, status=400)
    except Exception as e:  # noqa: BLE001
        logger.exception("Error in word_count")
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)
