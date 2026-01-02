"""Anki file generation utilities."""

import io
import random

import genanki
from django.core.files.base import ContentFile
from django.db.models import QuerySet
from django.utils import timezone

from lexiflux.anki.anki_common import create_anki_notes_data, get_anki_model_config
from lexiflux.models import Language, TranslationHistory


def export_words_to_anki_file(  # pylint: disable=too-many-locals
    language: Language,
    terms: QuerySet[TranslationHistory],
    deck_name: str,
) -> tuple[ContentFile, str]:
    """Export words to an Anki-compatible file."""
    model_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311
    model_config = get_anki_model_config("Lexiflux Translation Model")

    model = genanki.Model(
        model_id,
        model_config["modelName"],
        fields=[{"name": field} for field in model_config["inOrderFields"]],
        templates=[
            {
                "name": template["Name"],
                "qfmt": template["Front"],
                "afmt": template["Back"],
            }
            for template in model_config["cardTemplates"]
        ],
        css=model_config["css"],
    )

    deck_id = random.randrange(1 << 30, 1 << 31)  # noqa: S311
    deck = genanki.Deck(deck_id, deck_name)

    for term in terms:
        notes_data = create_anki_notes_data(term, model.name, deck_name)
        for note_data in notes_data:
            note = genanki.Note(
                model=model,
                fields=[note_data["fields"]["Front"], note_data["fields"]["Back"]],
                tags=note_data["tags"],
            )
            deck.add_note(note)

    package = genanki.Package(deck)
    filename = f"lexiflux_{language.google_code}_{timezone.now().strftime('%Y%m%d%H%M%S')}.apkg"

    file_buffer = io.BytesIO()
    package.write_to_file(file_buffer)
    file_buffer.seek(0)

    content_file = ContentFile(file_buffer.getvalue(), name=filename)

    return content_file, filename
