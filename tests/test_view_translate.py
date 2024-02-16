import pytest
from django.urls import reverse
from unittest.mock import patch

from lexiflux.language.translation import get_translator
from lexiflux.models import ReaderProfile


@pytest.mark.django_db
@patch('lexiflux.views.get_translator')
def test_translate_view_success(mock_get_translator, client, user):
    client.force_login(user)

    mock_translator = mock_get_translator.return_value
    mock_translator.translate.return_value = "Hola"

    book_code = 'alice-adventures-carroll'
    response = client.get(reverse('translate'), {
        'text': 'Hello',
        'book-code': book_code,  # Assuming a book ID is necessary but not used in the mock
    })

    assert response.status_code == 200
    assert response.json() == {
        'translatedText': 'Hola',
        'article': '<p>Hello</p>'
    }
    mock_get_translator.assert_called_once_with(book_code, user.id)
    mock_translator.translate.assert_called_once_with('Hello')


@patch('lexiflux.language.translation.Translator')  # Adjust the import path as necessary
def test_get_translator(mock_translator, book, user):
    book_code = book.code
    user_id = user.id

    result = get_translator(book_code, str(user_id))

    profile, created = ReaderProfile.objects.get_or_create(user=user)
    mock_translator.assert_called_once_with(book, profile)
    assert isinstance(result, mock_translator.return_value.__class__)