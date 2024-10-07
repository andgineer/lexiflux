import allure
import pytest
from unittest.mock import patch, MagicMock
from lexiflux.models import TranslationHistory, Language
from lexiflux.anki.anki_connect import create_anki_notes_data, get_anki_model_config, NOTES_PER_TERM
from lexiflux.anki.anki_file import export_words_to_anki_file
from lexiflux.anki.anki_connect import export_words_to_anki_connect
from lexiflux.anki.anki_connect import parse_error_message


@allure.epic('Pages endpoints')
@allure.story('Words export')
@allure.feature("Anki")
def test_export_words_to_anki_connect(book, approved_user):
    source_language = Language.objects.get(name="English")
    target_language = Language.objects.get(name="French")

    # Create some sample TranslationHistory objects
    translations = [
        TranslationHistory.objects.create(
            user=approved_user,
            book=book,
            term='apple',
            translation='pomme',
            context=f'{TranslationHistory.CONTEXT_MARK}before {TranslationHistory.CONTEXT_MARK} after{TranslationHistory.CONTEXT_MARK}',
            source_language=source_language,
            target_language=target_language
        ),
        TranslationHistory.objects.create(
            user=approved_user,
            book=book,
            term='book',
            translation='livre',
            context=f'{TranslationHistory.CONTEXT_MARK}before {TranslationHistory.CONTEXT_MARK} after{TranslationHistory.CONTEXT_MARK}',
            source_language=source_language,
            target_language=target_language
        )
    ]

    with patch('lexiflux.anki.anki_connect.requests.post') as mock_post:
        mock_post.return_value.json.return_value = {'result': [1, 2, 3, 4, 5, 6]}

        result = export_words_to_anki_connect(book.language, translations, "Test Deck")

        assert result == 2  # We expect 2 words to be exported
        assert mock_post.call_count == 3  # createDeck, createModel, addNotes


@allure.epic('Pages endpoints')
@allure.story('Words export')
@allure.feature("Anki")
def test_create_anki_notes():
    term = TranslationHistory(
        term='hello',
        translation='bonjour',
        context=f'{TranslationHistory.CONTEXT_MARK}before {TranslationHistory.CONTEXT_MARK} world{TranslationHistory.CONTEXT_MARK}'
    )

    notes = create_anki_notes_data(term, "Test Model", "Test Deck")

    assert len(notes) == 3
    assert notes[0]['fields']['Front'] == 'hello'
    assert 'bonjour' in notes[0]['fields']['Back']
    assert 'hello world' in notes[0]['fields']['Back']


@allure.epic('Pages endpoints')
@allure.story('Words export')
@allure.feature("Anki")
@pytest.mark.parametrize("error_message, expected_result", [
    ("['duplicate']", ['duplicate']),
    ("Invalid input", ["Invalid input"])
])
def test_parse_error_message(error_message, expected_result):
    result = parse_error_message(error_message)
    assert result == expected_result


@allure.epic('Pages endpoints')
@allure.story('Words export')
@allure.feature("Anki")
def test_export_words_to_anki_file(book, approved_user):
    source_language, _ = Language.objects.get_or_create(name="English")
    target_language, _ = Language.objects.get_or_create(name="French")

    translations = [
        TranslationHistory.objects.create(
            user=approved_user,
            book=book,
            term='apple',
            translation='pomme',
            context=f'{TranslationHistory.CONTEXT_MARK}before {TranslationHistory.CONTEXT_MARK} after{TranslationHistory.CONTEXT_MARK}',
            source_language=source_language,
            target_language=target_language
        )
    ]

    with patch('lexiflux.anki.anki_file.genanki.Package.write_to_file'):
        content_file, filename = export_words_to_anki_file(book.language, translations, "Test Deck")

    assert content_file is not None
    assert filename.startswith('lexiflux_en_')
    assert filename.endswith('.apkg')
