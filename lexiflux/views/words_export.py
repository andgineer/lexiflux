"""Views for exporting words to Anki or other cards learning apps."""

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

    context = {
        "languages": json.dumps(list(languages)),
        "language_groups": json.dumps(list(language_groups)),
        "default_selection": language_selection,
        "last_export_datetime": last_export_date,
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

        if export_method == "ankiConnect":
            words_exported = export_words_to_anki_connect(language, terms)
            response_data = {"status": "success", "exported_words": words_exported}
            response = JsonResponse(response_data)
        elif export_method == "ankiFile":
            file, words_exported, filename = export_words_to_anki_file(language, terms)
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


def export_words_to_anki_file(  # pylint: disable=too-many-locals
    language: Language, terms: List[TranslationHistory]
) -> tuple[ContentFile, int, str]:
    """Export words to an Anki-compatible file."""
    model_id = random.randrange(1 << 30, 1 << 31)

    # Define the note model
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

    # Create a unique deck ID
    deck_id = random.randrange(1 << 30, 1 << 31)

    # Create the deck
    deck = genanki.Deck(deck_id, f"Lexiflux - {language.name}")

    for term in terms:
        # Extract the sentence and word position from the context
        context_parts = term.context.split(TranslationHistory.CONTEXT_MARK)
        # before_sentence = context_parts[0]
        sentence_start = context_parts[1]
        sentence_end = context_parts[2]
        # after_sentence = context_parts[3] if len(context_parts) > 3 else ""

        # Reconstruct the full sentence with the term
        full_sentence = f"{sentence_start}{term.term}{sentence_end}"

        # Create sentence with blank
        sentence_with_blank = f"{sentence_start}_____{sentence_end}"

        # Card 1: Term on front, translation and context on back
        note1 = genanki.Note(
            model=model, fields=[term.term, f"{term.translation}<br><br>{term.context}"]
        )
        deck.add_note(note1)

        # Card 2: Sentence with blank on front, full sentence and translation on back
        note2 = genanki.Note(
            model=model,
            fields=[
                sentence_with_blank,
                f"{full_sentence}<br><br>{term.translation}<br><br>{term.context}",
            ],
        )
        deck.add_note(note2)

        # Card 3: Translation on front, term and context on back
        note3 = genanki.Note(
            model=model,
            fields=[term.translation, f"{term.term}<br><br>{full_sentence}<br><br>{term.context}"],
        )
        deck.add_note(note3)

    # Create the package
    package = genanki.Package(deck)

    # Generate a unique filename
    filename = f"anki_export_{language.google_code}_{timezone.now().strftime('%Y%m%d%H%M%S')}.apkg"

    # Save the package to a bytes object
    file_buffer = io.BytesIO()
    package.write_to_file(file_buffer)
    file_buffer.seek(0)

    # Convert to ContentFile
    content_file = ContentFile(file_buffer.getvalue(), name=filename)

    return content_file, len(terms) * 3, filename
