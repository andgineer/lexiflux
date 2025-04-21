import json

import allure
import pytest
from unittest.mock import patch, MagicMock

import requests

from lexiflux.models import TranslationHistory, Language
from lexiflux.anki.anki_connect import create_anki_notes_data, add_notes
from lexiflux.anki.anki_file import export_words_to_anki_file
from lexiflux.anki.anki_connect import export_words_to_anki_connect
from lexiflux.anki.anki_connect import parse_error_message


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_export_words_to_anki_connect(book, approved_user):
    source_language = Language.objects.get(name="English")
    target_language = Language.objects.get(name="French")

    # Create some sample TranslationHistory objects
    translations = [
        TranslationHistory.objects.create(
            user=approved_user,
            book=book,
            term="apple",
            translation="pomme",
            context=f"{TranslationHistory.CONTEXT_MARK}before {TranslationHistory.CONTEXT_MARK} after{TranslationHistory.CONTEXT_MARK}",
            source_language=source_language,
            target_language=target_language,
        ),
        TranslationHistory.objects.create(
            user=approved_user,
            book=book,
            term="book",
            translation="livre",
            context=f"{TranslationHistory.CONTEXT_MARK}before {TranslationHistory.CONTEXT_MARK} after{TranslationHistory.CONTEXT_MARK}",
            source_language=source_language,
            target_language=target_language,
        ),
    ]

    with patch("lexiflux.anki.anki_connect.requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"result": [1, 2, 3, 4, 5, 6]}

        result = export_words_to_anki_connect(book.language, translations, "Test Deck")

        assert result == 2  # We expect 2 words to be exported
        assert mock_post.call_count == 3  # createDeck, createModel, addNotes


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_create_anki_notes():
    term = TranslationHistory(
        term="hello",
        translation="bonjour",
        context=f"{TranslationHistory.CONTEXT_MARK}before {TranslationHistory.CONTEXT_MARK} world{TranslationHistory.CONTEXT_MARK}",
    )

    notes = create_anki_notes_data(term, "Test Model", "Test Deck")

    assert len(notes) == 3
    assert notes[0]["fields"]["Front"] == "hello"
    assert "bonjour" in notes[0]["fields"]["Back"]
    assert "hello world" in notes[0]["fields"]["Back"]


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
@pytest.mark.parametrize(
    "error_message, expected_result",
    [("['duplicate']", ["duplicate"]), ("Invalid input", ["Invalid input"])],
)
def test_parse_error_message(error_message, expected_result):
    result = parse_error_message(error_message)
    assert result == expected_result


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_export_words_to_anki_file(book, approved_user):
    source_language, _ = Language.objects.get_or_create(name="English")
    target_language, _ = Language.objects.get_or_create(name="French")

    translations = [
        TranslationHistory.objects.create(
            user=approved_user,
            book=book,
            term="apple",
            translation="pomme",
            context=f"{TranslationHistory.CONTEXT_MARK}before {TranslationHistory.CONTEXT_MARK} after{TranslationHistory.CONTEXT_MARK}",
            source_language=source_language,
            target_language=target_language,
        )
    ]

    with patch("lexiflux.anki.anki_file.genanki.Package.write_to_file"):
        content_file, filename = export_words_to_anki_file(book.language, translations, "Test Deck")

    assert content_file is not None
    assert filename.startswith("lexiflux_en_")
    assert filename.endswith(".apkg")


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_export_words_to_anki_connect_connection_error(book, approved_user):
    """Test handling connection errors to AnkiConnect."""
    source_language = Language.objects.get(name="English")
    target_language = Language.objects.get(name="French")

    translations = [
        TranslationHistory.objects.create(
            user=approved_user,
            book=book,
            term="apple",
            translation="pomme",
            context=f"{TranslationHistory.CONTEXT_MARK}before {TranslationHistory.CONTEXT_MARK} after{TranslationHistory.CONTEXT_MARK}",
            source_language=source_language,
            target_language=target_language,
        ),
    ]

    with patch("lexiflux.anki.anki_connect.requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        with pytest.raises(ValueError) as excinfo:
            export_words_to_anki_connect(book.language, translations, "Test Deck")

        assert "Failed to connect to AnkiConnect" in str(excinfo.value)


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_export_words_with_timeout(book, approved_user):
    """Test handling timeout when connecting to AnkiConnect."""
    source_language = Language.objects.get(name="English")
    target_language = Language.objects.get(name="French")

    translations = [
        TranslationHistory.objects.create(
            user=approved_user,
            book=book,
            term="apple",
            translation="pomme",
            context=f"{TranslationHistory.CONTEXT_MARK}before {TranslationHistory.CONTEXT_MARK} after{TranslationHistory.CONTEXT_MARK}",
            source_language=source_language,
            target_language=target_language,
        ),
    ]

    with patch("lexiflux.anki.anki_connect.requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(requests.exceptions.Timeout) as excinfo:
            export_words_to_anki_connect(book.language, translations, "Test Deck")

        assert "Request timed out" in str(excinfo.value)


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_add_notes_all_duplicates():
    """Test adding notes where all are duplicates."""
    notes = [
        {"deckName": "Test", "modelName": "Test", "fields": {"Front": "hello", "Back": "bonjour"}},
        {"deckName": "Test", "modelName": "Test", "fields": {"Front": "world", "Back": "monde"}},
    ]

    with patch("lexiflux.anki.anki_connect.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "['duplicate', 'duplicate']"}
        mock_post.return_value = mock_response

        result = add_notes("http://localhost:8765", notes)

        assert result == 2  # Two duplicates skipped


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_add_notes_mixed_results():
    """Test adding notes with mixed results (some duplicates, some added)."""
    notes = [
        {"deckName": "Test", "modelName": "Test", "fields": {"Front": "hello", "Back": "bonjour"}},
        {"deckName": "Test", "modelName": "Test", "fields": {"Front": "world", "Back": "monde"}},
    ]

    with patch("lexiflux.anki.anki_connect.requests.post") as mock_post:
        # First call returns error for mixed results
        first_response = MagicMock()
        first_response.json.return_value = {"error": "['duplicate', 'other error']"}

        # Second call for individual notes
        individual_responses = [
            MagicMock(),  # For first note
            MagicMock(),  # For second note
        ]
        individual_responses[0].json.return_value = {"error": "['duplicate']"}
        individual_responses[1].json.return_value = {"result": [123]}

        mock_post.side_effect = [first_response] + individual_responses

        result = add_notes("http://localhost:8765", notes)

        assert result == 1  # One duplicate skipped, one added


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_add_notes_unexpected_error():
    """Test adding notes with an unexpected error."""
    notes = [
        {"deckName": "Test", "modelName": "Test", "fields": {"Front": "hello", "Back": "bonjour"}},
    ]

    with patch("lexiflux.anki.anki_connect.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Critical Anki error"}
        mock_post.return_value = mock_response

        with pytest.raises(ValueError) as excinfo:
            add_notes("http://localhost:8765", notes)

        assert "AnkiConnect error: Critical Anki error" in str(excinfo.value)


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_add_notes_http_error():
    """Test handling HTTP errors from AnkiConnect."""
    notes = [
        {"deckName": "Test", "modelName": "Test", "fields": {"Front": "hello", "Back": "bonjour"}},
    ]

    with patch("lexiflux.anki.anki_connect.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "502 Bad Gateway"
        )
        mock_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            add_notes("http://localhost:8765", notes)


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_add_notes_invalid_json():
    """Test handling invalid JSON responses from AnkiConnect."""
    notes = [
        {"deckName": "Test", "modelName": "Test", "fields": {"Front": "hello", "Back": "bonjour"}},
    ]

    with patch("lexiflux.anki.anki_connect.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response

        with pytest.raises(ValueError) as excinfo:
            add_notes("http://localhost:8765", notes)

        assert "Received an invalid response from AnkiConnect" in str(excinfo.value)


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_add_notes_missing_result():
    """Test handling responses without 'result' field from AnkiConnect."""
    notes = [
        {"deckName": "Test", "modelName": "Test", "fields": {"Front": "hello", "Back": "bonjour"}},
    ]

    with patch("lexiflux.anki.anki_connect.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}  # Missing 'result' field
        mock_post.return_value = mock_response

        with pytest.raises(ValueError) as excinfo:
            add_notes("http://localhost:8765", notes)

        assert "Unexpected response format from AnkiConnect" in str(excinfo.value)


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
def test_add_notes_mismatched_count():
    """Test handling responses with mismatched result count from AnkiConnect."""
    notes = [
        {"deckName": "Test", "modelName": "Test", "fields": {"Front": "hello", "Back": "bonjour"}},
        {"deckName": "Test", "modelName": "Test", "fields": {"Front": "world", "Back": "monde"}},
    ]

    with patch("lexiflux.anki.anki_connect.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": [123]}  # Only one result for two notes
        mock_post.return_value = mock_response

        with pytest.raises(AssertionError) as excinfo:
            add_notes("http://localhost:8765", notes)

        assert "Mismatch between number of notes and response" in str(excinfo.value)


@allure.epic("Pages endpoints")
@allure.story("Words export")
@allure.feature("Anki")
@pytest.mark.parametrize(
    "error_message, expected_result",
    [
        ("['duplicate', 'invalid format']", ["duplicate", "invalid format"]),
        ("", [""]),  # Empty error message
        ("{malformed: json}", ["{malformed: json}"]),  # Malformed JSON
    ],
)
def test_parse_error_message_extended(error_message, expected_result):
    """Extended tests for parse_error_message with additional cases."""
    from lexiflux.anki.anki_connect import parse_error_message

    result = parse_error_message(error_message)
    assert result == expected_result
