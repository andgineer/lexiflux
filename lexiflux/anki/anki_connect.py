"""AnkiConnect API for exporting words to Anki."""

import json
import logging
from typing import List, Optional, Dict, Any
import ast
import requests

import urllib3.connection

from lexiflux.models import Language, TranslationHistory
from lexiflux.anki.anki_common import create_anki_notes_data, get_anki_model_config, NOTES_PER_TERM

ANKI_CONNECT_TIMEOUT = 10

logger = logging.getLogger(__name__)

ANKI_CONNECT_URL = "http://localhost:8765"


def export_words_to_anki_connect(  # pylint: disable=unused-argument
    language: Language, terms: List[TranslationHistory], deck_name: str
) -> int:
    """Export words to Anki using AnkiConnect."""
    anki_connect_url = ANKI_CONNECT_URL

    try:
        create_deck(anki_connect_url, deck_name)

        model_name = "Lexiflux Translation Model"
        create_model(anki_connect_url, model_name)

        notes = []
        for term in terms:
            notes.extend(create_anki_notes_data(term, model_name, deck_name))

        skipped_count = add_notes(anki_connect_url, notes)
        return (  # type: ignore
            len(terms) - skipped_count // NOTES_PER_TERM
            if skipped_count is not None
            else len(terms)
        )

    except (requests.exceptions.ConnectionError, urllib3.exceptions.MaxRetryError) as e:
        logger.error(f"Failed to connect to AnkiConnect: {str(e)}")
        raise ValueError(
            "Failed to connect to AnkiConnect. "
            'Is <a href="https://apps.ankiweb.net/">Anki</a> running '
            'with <a href="https://ankiweb.net/shared/info/2055492159">AnkiConnect addon?</a>'
        ) from e


def create_deck(url: str, deck_name: str) -> None:
    """Create a new deck if it doesn't exist."""
    payload = {"action": "createDeck", "version": 6, "params": {"deck": deck_name}}
    requests.post(url, json=payload, timeout=ANKI_CONNECT_TIMEOUT)


def create_model(url: str, model_name: str) -> None:
    """Create a new note type if it doesn't exist."""
    payload = {
        "action": "createModel",
        "version": 6,
        "params": get_anki_model_config(model_name),
    }
    requests.post(url, json=payload, timeout=ANKI_CONNECT_TIMEOUT)


def add_notes(url: str, notes: List[Dict[str, Any]]) -> Optional[int]:
    """Add notes to Anki, skipping duplicates and adding only new notes.

    Return None if all success.
    Or the number of duplicate notes skipped.
    Raises exceptions on errors.
    """
    payload = {"action": "addNotes", "version": 6, "params": {"notes": notes}}
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        logger.info(f"result {result}")

        if "error" in result and result["error"] is not None:
            error_list = parse_error_message(result["error"])
            if len(error_list) == len(notes) and all(
                "duplicate" in str(err).lower() for err in error_list
            ):
                logger.info(f"All {len(notes)} notes are duplicates. No new notes added.")
                return len(notes)
            if any("duplicate" in str(err).lower() for err in error_list):
                # Some notes are duplicates, but others might have been added successfully
                logger.info("Some notes are duplicates. Adding individually.")
                added_count = sum(add_notes(url, [note]) is None for note in notes)
                return len(notes) - added_count
            logger.error("Unexpected AnkiConnect errors")
            raise ValueError(f"AnkiConnect error: {result['error']}")
        if "result" not in result:
            raise ValueError("Unexpected response format from AnkiConnect")
        assert len(result["result"]) == len(notes), "Mismatch between number of notes and response"
        return None

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AnkiConnect response: {str(e)}")
        raise ValueError("Received an invalid response from AnkiConnect") from e
    except Exception as e:
        logger.error(f"Unexpected error when adding notes to Anki: {str(e)}")
        raise


def parse_error_message(error_message: str) -> List[str]:
    """Parse the error message string into a list of error messages."""
    try:
        return ast.literal_eval(error_message)  # type: ignore
    except (ValueError, SyntaxError):
        return [error_message]  # Return as a single-item list if parsing fails
