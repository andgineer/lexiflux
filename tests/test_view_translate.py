import pytest
from django.urls import reverse
from unittest.mock import patch

@pytest.mark.django_db
@patch('lexiflux.views.get_translator')
def test_translate_view_success(mock_get_translator, client, user):
    client.force_login(user)

    mock_translator = mock_get_translator.return_value
    mock_translator.translate.return_value = "Hola"

    response = client.get(reverse('translate'), {
        'text': 'Hello',
        'book-id': '1',  # Assuming a book ID is necessary but not used in the mock
    })

    assert response.status_code == 200
    assert response.json() == {
        'translatedText': 'Hola',
        'article': '<p>Hello</p>'
    }
    mock_get_translator.assert_called_once_with('1', user.id)
    mock_translator.translate.assert_called_once_with('Hello')

