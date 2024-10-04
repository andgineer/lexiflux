"""Views for exporting words to Anki or other cards learning apps."""

import csv
import io
import json
import logging
import random
from typing import Any, List

import genanki
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpRequest, HttpResponse, FileResponse
from django.utils.timezone import is_naive, make_aware
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Max

from lexiflux.decorators import smart_login_required
from lexiflux.models import (
    Language,
    LanguageGroup,
    TranslationHistory,
    WordsExport,
    LanguagePreferences,
)

logger = logging.getLogger(__name__)


@smart_login_required  # type: ignore
def words_export_page(request: HttpRequest) -> HttpResponse:
    """Render the words export page with all necessary data."""
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
        .prefetch_related("languages")
        .values("id", "name")
    )

    # Check if translation history is empty
    has_translations = TranslationHistory.objects.filter(user=user).exists()

    if not has_translations:
        context = {
            "languages": json.dumps([]),
            "language_groups": json.dumps([]),
            "default_selection": None,
            "last_export_datetime": None,
            "no_translations": json.dumps(True),
            "initial_word_count": 0,
        }
        logger.info("No translations found for the user")
        return render(request, "words-export.html", context)

    language_prefs = LanguagePreferences.get_or_create_language_preferences(
        user, user.default_language_preferences.language
    )

    language_selection = next(
        (
            lang["google_code"]
            for lang in languages
            if lang["google_code"] == language_prefs.language.google_code
        ),
        None,
    )
    # If last used language is not in translation history, use the first language
    if language_selection is None and languages:
        language_selection = languages[0]["google_code"]

    # Get the last export datetime for the default selection
    last_export = None
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
            "google_code", flat=True
        )
        if language_selection in group_languages:
            language_selection = group["id"]
            break

    initial_word_count = TranslationHistory.objects.filter(
        user=user,
        source_language=language if language_selection else None,
        last_lookup__gte=timezone.datetime.fromisoformat(last_export_date),
    ).count()

    context = {
        "languages": json.dumps(list(languages)),
        "language_groups": json.dumps(list(language_groups)),
        "default_selection": language_selection,
        "last_export_datetime": last_export_date,
        "no_translations": json.dumps(False),
        "initial_word_count": initial_word_count,
    }

    return render(request, "words-export.html", context)


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
def last_export_datetime(request: HttpRequest) -> HttpResponse:  # pylint: disable=too-many-return-statements
    """Get the last export datetime for a given language or language group."""
    try:
        language_id = request.GET.get("language")
        user = request.user

        if not language_id:
            return JsonResponse({"error": "Language parameter is required"}, status=400)

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
            last_export = last_export.export_datetime if last_export else None

        logger.info(f"For language {language_id} last export datetime: {last_export}")

        if last_export:
            return JsonResponse({"last_export_datetime": last_export.isoformat()})
        # Return a default date if no export exists
        default_date = timezone.datetime(timezone.now().year, 1, 1).isoformat()
        return JsonResponse({"last_export_datetime": default_date})

    except LanguageGroup.DoesNotExist:
        return JsonResponse({"error": "Language group not found"}, status=404)
    except Language.DoesNotExist:
        return JsonResponse({"error": "Language not found"}, status=404)
    except ValueError:
        return JsonResponse({"error": "Invalid language or language group ID"}, status=400)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error in last_export_datetime: {str(e)}", exc_info=True)
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)


@smart_login_required
@require_http_methods(["POST"])  # type: ignore
def export_words(request: HttpRequest) -> HttpResponse:
    """Export words for the given language or language group."""
    data = json.loads(request.body)
    language_id = data.get("language")
    export_method = data.get("export_method")
    min_datetime = timezone.datetime.fromisoformat(data.get("min_datetime"))
    if is_naive(min_datetime):
        min_datetime = make_aware(min_datetime)
    user = request.user

    try:
        if isinstance(language_id, str) and language_id.isdigit():  # It's a language group
            group = LanguageGroup.objects.get(id=int(language_id))
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

        words_exported = len(terms)

        if export_method == "ankiConnect":
            export_words_to_anki_connect(language, terms)
            response_data = {"status": "success", "exported_words": words_exported}
            response = JsonResponse(response_data)
        elif export_method == "ankiFile":
            file, filename = export_words_to_anki_file(language, terms)
            response = FileResponse(file, as_attachment=True, filename=filename)
        elif export_method == "csvFile":
            file, filename = export_words_to_csv_file(language, terms)
            response = FileResponse(file, as_attachment=True, filename=filename)
        else:
            raise ValueError("Invalid export method")

        WordsExport.objects.create(
            user=user,
            language=language,
            word_count=words_exported,
            details={"format": export_method},
        )

        logger.info(
            f"Words exported for {language.name}: {words_exported} words using {export_method}"
        )
        return response
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error exporting words: {str(e)}", exc_info=True)
        return JsonResponse({"status": "error", "error": str(e)})


def export_words_to_anki_connect(language: Language, terms: Any) -> int:  # pylint: disable=unused-argument
    """Export words to Anki using AnkiConnect."""
    # TODO: Implement AnkiConnect integration
    # This function should use the AnkiConnect API to add cards to Anki
    # Return the number of words exported
    return len(terms)


def export_words_to_anki_file(
    language: Language, terms: List[TranslationHistory]
) -> tuple[ContentFile, str]:
    """Export words to an Anki-compatible file."""
    model_id = random.randrange(1 << 30, 1 << 31)

    model = genanki.Model(
        model_id,
        "Lexiflux Translation Model",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
            },
        ],
    )

    deck_id = random.randrange(1 << 30, 1 << 31)
    deck = genanki.Deck(deck_id, f"Lexiflux - {language.name}")

    for term in terms:
        notes = create_anki_notes(term, model)
        for note in notes:
            deck.add_note(note)

    package = genanki.Package(deck)
    filename = (
        f"lexiflux_{language.google_code}_" f"{timezone.now().strftime('%Y%m%d%H%M%S')}.apkg"
    )

    file_buffer = io.BytesIO()
    package.write_to_file(file_buffer)
    file_buffer.seek(0)

    content_file = ContentFile(file_buffer.getvalue(), name=filename)

    return content_file, filename


def create_anki_notes(term: TranslationHistory, model: genanki.Model) -> List[genanki.Note]:
    """Create Anki notes for a given term."""
    context_parts = term.context.split(TranslationHistory.CONTEXT_MARK)
    sentence_start = context_parts[1]
    sentence_end = context_parts[2]

    full_sentence = f"{sentence_start}{term.term}{sentence_end}"
    sentence_with_blank = f"{sentence_start}__({term.translation})___{sentence_end}"

    return [
        genanki.Note(
            model=model,
            fields=[term.term, f"{term.translation}<br><br>{full_sentence}"],
        ),
        genanki.Note(
            model=model,
            fields=[
                sentence_with_blank,
                f"{term.term} ({term.translation})<br><br>{full_sentence}",
            ],
        ),
        genanki.Note(
            model=model,
            fields=[term.translation, f"{term.term}<br><br>{full_sentence}"],
        ),
    ]


def export_words_to_csv_file(
    language: Language, terms: List[TranslationHistory]
) -> tuple[ContentFile, str]:
    """Export words to a CSV file."""
    filename = f"lexiflux_{language.google_code}_" f"{timezone.now().strftime('%Y%m%d%H%M%S')}.csv"

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(["Term", "Translation", "Language", "Translation Language", "Sentence"])

    for term in terms:
        context_parts = term.context.split(TranslationHistory.CONTEXT_MARK)
        sentence_start = context_parts[1]
        sentence_end = context_parts[2]

        full_sentence = f"{sentence_start}_____{sentence_end}"

        writer.writerow(
            [
                term.term,
                term.translation,
                term.source_language.name,
                term.target_language.name,
                full_sentence,
            ]
        )

    output.seek(0)
    content_file = ContentFile(output.getvalue().encode("utf-8"), name=filename)

    return content_file, filename


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
                {"error": "Language and min_datetime parameters are required"}, status=400
            )

        min_datetime = timezone.datetime.fromisoformat(min_datetime)
        if is_naive(min_datetime):
            min_datetime = make_aware(min_datetime)

        if language_id.isdigit():  # It's a language group
            group = LanguageGroup.objects.get(id=int(language_id))
            exported_words_count = TranslationHistory.objects.filter(
                user=user, source_language__in=group.languages.all(), last_lookup__gte=min_datetime
            ).count()
        else:  # It's a language
            language = Language.objects.get(google_code=language_id)
            exported_words_count = TranslationHistory.objects.filter(
                user=user, source_language=language, last_lookup__gte=min_datetime
            ).count()

        return JsonResponse({"word_count": exported_words_count})

    except (LanguageGroup.DoesNotExist, Language.DoesNotExist):
        return JsonResponse({"error": "Language or language group not found"}, status=404)
    except ValueError:
        return JsonResponse({"error": "Invalid language ID or datetime format"}, status=400)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error in word_count: {str(e)}", exc_info=True)
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)
