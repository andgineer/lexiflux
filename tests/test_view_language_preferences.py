from unittest.mock import patch

import allure
import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed


@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
def test_language_preferences_access_denied(client, book):
    # Access without login
    response = client.get(reverse('language-preferences'), {'book-code': book.code})

    assert response.status_code == 302
    assert response.url.startswith('/accounts/login'), "User should be redirected to login page"


@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
@pytest.mark.skip(reason="Fix the test")
def test_language_preferences_skip_auth_access(client, book):
    with patch.dict('os.environ', {'LEXIFLUX_SKIP_AUTH': 'true'}):
        response = client.get(reverse('language-preferences'), {'book-code': book.code})

    assert response.status_code == 302
    assert response.url.startswith('/accounts/login'), "User should be redirected to login page"


@allure.epic('Pages endpoints')
@allure.story('Language Preferences')
@pytest.mark.django_db
def test_language_preferences_view_success(client, user):
    client.force_login(user)

    response = client.get(reverse('language-preferences'))

    assert response.status_code == 200

    assertTemplateUsed(response, 'language-preferences.html')
