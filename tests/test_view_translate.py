import allure
import pytest
from django.urls import reverse
from unittest.mock import patch, MagicMock

import lexiflux.views.lexical_views
from lexiflux.language.translation import get_translator, Translator, AVAILABLE_TRANSLATORS
from lexiflux.models import LanguagePreferences


@allure.epic('Translator')
@pytest.mark.django_db
@patch('lexiflux.views.lexical_views.get_translator')
def test_translate_view_success(mock_get_translator, client, user, book):
    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(user=user, language=book.language)

    mock_translator = mock_get_translator.return_value
    mock_translator.translate.return_value = "Hola"

    book_code = 'some-book-code'
    response = client.get(reverse('translate'), {
        "lexical-article": "0",
        'text': 'Hello',
        'book-code': book_code,
        'book-page-number': '1',
        'word-ids': '1.2.3',
    })

    assert response.status_code == 200
    assert response.json() == {"article": 'Hola'}
    mock_get_translator.assert_called_once_with("GoogleTranslator", book.language.name.lower(), language_preferences.user_language.name.lower())
    mock_translator.translate.assert_called_once_with('of page 1')


@allure.epic('Translator')
@patch('lexiflux.language.translation.Translator')  # Adjust the import path as necessary
def test_get_translator(mock_translator, book, user):
    language_preferences = LanguagePreferences.get_or_create_language_preferences(user=user, language=book.language)

    result = get_translator("GoogleTranslator", book.language.name.lower(), language_preferences.user_language.name.lower())
    mock_translator.assert_called_once_with("GoogleTranslator", book.language.name.lower(), language_preferences.user_language.name.lower())
    assert isinstance(result, mock_translator.return_value.__class__)


@allure.epic('Translator')
@pytest.mark.django_db
def test_translator_translate(book, user):
    mock_translation = "This is a test translation."

    # Mock the specific translator class (GoogleTranslator in this case)
    with patch.dict(AVAILABLE_TRANSLATORS, {
        "GoogleTranslator": (MagicMock(), "Google Translator")
    }) as mock_translators:
        mock_google_translator = mock_translators["GoogleTranslator"][0].return_value
        mock_google_translator.translate.return_value = mock_translation

        language_preferences = LanguagePreferences.get_or_create_language_preferences(user=user, language=book.language)
        translator = Translator(
            "GoogleTranslator",
            book.language.google_code,
            language_preferences.user_language.google_code
        )
        result = translator.translate("This is a test.")

        assert result == mock_translation
        mock_google_translator.translate.assert_called_once_with("This is a test.")
