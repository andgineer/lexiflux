"""Anki file generation utilities."""

import io
import random
from typing import List

import genanki
from django.core.files.base import ContentFile
from django.utils import timezone

from lexiflux.models import TranslationHistory, Language


def export_words_to_anki_file(
    language: Language, terms: List[TranslationHistory], deck_name: str
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
    deck = genanki.Deck(deck_id, deck_name)

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
