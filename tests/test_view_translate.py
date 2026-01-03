import allure
import pytest
from django.urls import reverse
from unittest.mock import patch, MagicMock

from lexiflux.language.translation import get_translator, Translator, AVAILABLE_TRANSLATORS
from lexiflux.models import LanguagePreferences
from tests.conftest import USER_PASSWORD


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
@patch("lexiflux.views.lexical_views.get_translator")
def test_translate_view_success(mock_get_translator, client, user, book):
    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )

    mock_translator = mock_get_translator.return_value
    mock_translator.translate.return_value = "Hola"

    book_code = "some-book-code"
    response = client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "text": "Hello",
            "book-code": book_code,
            "book-page-number": "1",
            "word-ids": "1.2.3",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"article": "Hola"}
    mock_get_translator.assert_called_once_with(
        "GoogleTranslator",
        book.language.name.lower(),
        language_preferences.user_language.name.lower(),
    )
    mock_translator.translate.assert_called_once_with("of page 1")


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@patch("lexiflux.language.translation.Translator")
def test_get_translator(mock_translator, book, user):
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )

    result = get_translator(
        "GoogleTranslator",
        book.language.name.lower(),
        language_preferences.user_language.name.lower(),
    )
    mock_translator.assert_called_once_with(
        "GoogleTranslator",
        book.language.name.lower(),
        language_preferences.user_language.name.lower(),
    )
    assert isinstance(result, mock_translator.return_value.__class__)


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_view_approved_users_only(client, user, book):
    # force_login() skip auth backed, so we do full login here
    client.login(username=user.username, password=USER_PASSWORD)  # user.password is hashed

    book_code = "some-book-code"
    response = client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "text": "Hello",
            "book-code": book_code,
            "book-page-number": "1",
            "word-ids": "1.2.3",
        },
    )
    assert response.status_code == 302
    assert "login/?next=" in response.url


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translator_translate(book, user):
    mock_translation = "This is a test translation."

    # Mock the specific translator class (GoogleTranslator in this case)
    with patch.dict(
        AVAILABLE_TRANSLATORS, {"GoogleTranslator": (MagicMock(), "Google Translator")}
    ) as mock_translators:
        mock_google_translator = mock_translators["GoogleTranslator"][0].return_value
        mock_google_translator.translate.return_value = mock_translation

        language_preferences = LanguagePreferences.get_or_create_language_preferences(
            user=user, language=book.language
        )
        translator = Translator(
            "GoogleTranslator",
            book.language.google_code,
            language_preferences.user_language.google_code,
        )
        result = translator.translate("This is a test.")

        assert result == mock_translation
        mock_google_translator.translate.assert_called_once_with("This is a test.")


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_translate_view_retired_model_error(client, user, book):
    """Test that retired model error shows friendly HTML error message"""

    client.force_login(user)
    language_preferences = LanguagePreferences.get_or_create_language_preferences(
        user=user, language=book.language
    )
    # Set to an AI model type that would use LLM
    language_preferences.inline_translation_type = "Translate"
    language_preferences.inline_translation_parameters = {
        "model": "claude-sonnet-4-0"  # This model doesn't exist in chat_models.yaml
    }
    language_preferences.save()

    response = client.get(
        reverse("translate"),
        {
            "lexical-article": "0",
            "book-code": book.code,
            "book-page-number": "1",
            "word-ids": "1.2",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["error"] is True
    assert "AI Model No Longer Available" in data["article"]
    assert "claude-sonnet-4-0" in data["article"]
    assert "/language-preferences/" in data["article"]
