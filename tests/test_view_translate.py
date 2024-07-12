import allure
import pytest
from django.urls import reverse
from unittest.mock import patch

from lexiflux.language.translation import get_translator, Translator
from lexiflux.models import LanguagePreferences


@allure.epic('Translator')
@pytest.mark.django_db
@patch('lexiflux.views.get_translator')
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
    mock_get_translator.assert_called_once_with(book, language_preferences)
    mock_translator.translate.assert_called_once_with('of page 1')


@allure.epic('Translator')
@patch('lexiflux.language.translation.Translator')  # Adjust the import path as necessary
def test_get_translator(mock_translator, book, user):
    language_preferences = LanguagePreferences.get_or_create_language_preferences(user=user, language=book.language)

    result = get_translator(book, language_preferences)
    mock_translator.assert_called_once_with(book, language_preferences)
    assert isinstance(result, mock_translator.return_value.__class__)


@allure.epic('Translator')
@patch('lexiflux.language.translation.GoogleTranslator')
def test_translator_translate(mock_google_translator, book, user):
    mock_translation = "This is a test translation."
    mock_google_translator.return_value.translate.return_value = mock_translation

    language_preferences = LanguagePreferences.get_or_create_language_preferences(user=user, language=book.language)
    translator = Translator(book, language_preferences)
    result = translator.translate("This is a test.")

    assert result == mock_translation
    mock_google_translator.return_value.translate.assert_called_once_with("This is a test.")
