import allure
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client
from pytest_django.asserts import assertTemplateUsed

from lexiflux.models import ReadingLoc, ReadingHistory


@allure.epic('View: Location')
@pytest.mark.django_db
def test_location_view_updates_reading_location_successfully(client, user, book):
    client.force_login(user)
    book_id = book.id
    page_number = 1
    top_word = 10

    response = client.get(reverse('location'), {
        'book-code': book.code,
        'book-page-number': page_number,
        'top-word': top_word
    })

    assert response.status_code == 200, f"Failed to update reading location: {response.content}"
    assert ReadingLoc.objects.filter(
        user=user,
        book_id=book_id,
        page_number=page_number,
        word=top_word
    ).exists(), "Reading location should be updated in the database"


@allure.epic('View: Location')
@pytest.mark.django_db
def test_location_view_handles_invalid_parameters(client, user):
    client.force_login(user)

    # Intentionally omitting 'book-page-number' to trigger a 400 error
    response = client.get(reverse('location'), {
        'book-code': 'invalid',
        'top-word': 'not-an-int'
    })

    assert response.status_code == 400


@allure.epic('View: Location')
@pytest.mark.django_db
def test_location_view_enforces_access_control(client, user, book):
    # Create another user who does not have access to the book
    AnotherUser = get_user_model()
    another_user = AnotherUser.objects.create_user(username='another_user', password='67890', email="email")
    client.force_login(another_user)

    response = client.get(reverse('location'), {
        'book-code': book.code,
        'book-page-number': 1,
        'top-word': 10
    })

    assert response.status_code == 403, f"User should not be able to update reading location for a book they don't have access to: {response.content}"


@allure.epic('View: History')
@pytest.mark.django_db
def test_add_to_history_success(client, user, book):
    client.force_login(user)
    data = {
        'book_id': book.id,
        'page_number': 1,
        'top_word_id': 100
    }
    response = client.post(reverse('history'), data)

    assert response.status_code == 200
    assert ReadingHistory.objects.filter(user=user, book=book).exists()
    assert response.json() == {"message": "Reading history added successfully"}


@allure.epic('View: History')
@pytest.mark.django_db
def test_add_to_history_invalid_input(client, user):
    client.force_login(user)
    response = client.post(reverse('history'),
                           {'book_id': 'abc', 'page_number': 'xyz', 'top_word_id': 'invalid'})

    assert response.status_code == 400
    assert response.json() == {"error": "Invalid input"}


@allure.epic('View: Book')
@pytest.mark.django_db
def test_view_book_success(client, user, book):
    client.force_login(user)
    response = client.get(reverse('book'), {'book-code': book.code})

    assert response.status_code == 200
    assert 'book' in response.context
    assert response.context['book'].id == book.id
    assertTemplateUsed(response, 'book.html')


@allure.epic('View: Book')
@pytest.mark.django_db
def test_view_book_access_denied(client, book):
    # Assuming another_user does not have access to the book
    another_user = get_user_model().objects.create_user('another_user', 'another@example.com', 'password')
    client.force_login(another_user)
    response = client.get(reverse('book'), {'book-code': book.code})

    assert response.status_code == 403


@allure.epic('View: Profile')
@pytest.mark.django_db
def test_language_preferences_view_success(client, user):
    client.force_login(user)

    response = client.get(reverse('language-tool-preferences'))

    assert response.status_code == 200

    assertTemplateUsed(response, 'language-tool-preferences.html')