"""Common utilities for Anki export operations."""

from typing import Any

from lexiflux.models import TranslationHistory

NOTES_PER_TERM = 3


def create_anki_notes_data(
    term: TranslationHistory,
    model_name: str,
    deck_name: str,
) -> list[dict[str, Any]]:
    """Create Anki notes data for a given term."""
    context_parts = term.context.split(TranslationHistory.CONTEXT_MARK)
    sentence_start = context_parts[1]
    sentence_end = context_parts[2]

    full_sentence = f"{sentence_start}{term.term}{sentence_end}"
    sentence_with_blank = f"{sentence_start}__({term.translation})___{sentence_end}"

    return [
        {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": {"Front": term.term, "Back": f"{term.translation}<br><br>{full_sentence}"},
            "tags": ["lexiflux"],
        },
        {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": {
                "Front": sentence_with_blank,
                "Back": f"{term.term} ({term.translation})<br><br>{full_sentence}",
            },
            "tags": ["lexiflux"],
        },
        {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": {"Front": term.translation, "Back": f"{term.term}<br><br>{full_sentence}"},
            "tags": ["lexiflux"],
        },
    ]


def get_anki_model_config(model_name: str) -> dict[str, Any]:
    """Get the configuration for the Anki model."""
    return {
        "modelName": model_name,
        "inOrderFields": ["Front", "Back"],
        "css": (
            ".card { font-family: arial; font-size: 20px; "
            "text-align: center; color: black; background-color: white; }"
        ),
        "cardTemplates": [
            {
                "Name": "Card 1",
                "Front": "{{Front}}",
                "Back": "{{FrontSide}}<hr id='answer'>{{Back}}",
            },
        ],
    }
