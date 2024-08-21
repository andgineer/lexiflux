from unittest.mock import patch

import allure
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client
from pytest_django.asserts import assertTemplateUsed

from lexiflux.models import ReadingLoc


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_location_view_updates_reading_location_successfully(client, user, book):
    client.force_login(user)
    book_id = book.id
    page_number = 1
    top_word = 10

    response = client.post(reverse('location'), {
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


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_location_view_handles_invalid_parameters(client, user):
    client.force_login(user)

    # Intentionally omitting 'book-page-number' to trigger a 400 error
    response = client.post(reverse('location'), {
        'book-code': 'invalid',
        'top-word': 'not-an-int'
    })

    assert response.status_code == 400


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_location_view_enforces_access_control(client, user, book):
    # Create another user who does not have access to the book
    AnotherUser = get_user_model()
    another_user = AnotherUser.objects.create_user(username='another_user', password='67890', email="email")
    client.force_login(another_user)

    response = client.post(reverse('location'), {
        'book-code': book.code,
        'book-page-number': 1,
        'top-word': 10
    })

    assert response.status_code == 403, f"User should not be able to update reading location for a book they don't have access to: {response.content}"


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_jump_view_successful(client, user, book):
    client.force_login(user)

    # Create an initial ReadingLoc instance
    ReadingLoc.objects.create(
        user=user,
        book=book,
        page_number=1,
        word=0,
        jump_history=[{"page_number": 1, "word": 0}],
        current_jump=0
    )

    response = client.post(reverse('jump'), {
        'book-code': book.code,
        'book-page-number': 2,
        'top-word': 5
    })

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True

    # Verify that the database was updated
    reading_loc = ReadingLoc.objects.get(user=user, book=book)
    assert reading_loc.page_number == 2
    assert reading_loc.word == 5
    assert reading_loc.current_jump == 1
    assert reading_loc.jump_history == [{"page_number": 1, "word": 0}, {"page_number": 2, "word": 5}]


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_jump_view_invalid_parameters(client, user):
    client.force_login(user)
    response = client.post(reverse('jump'), {
        'book-code': 'invalid',
        'book-page-number': 'not-a-number',
        'top-word': 'not-a-number'
    })

    assert response.status_code == 400


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_jump_forward_view_successful(client, user, book):
    client.force_login(user)

    # Create a single ReadingLoc instance
    reading_loc = ReadingLoc.objects.create(user=user, book=book, page_number=2, word=10)

    # Simulate a jump history
    reading_loc.jump_history = [
        {"page_number": 1, "word": 0},
        {"page_number": 2, "word": 10},
        {"page_number": 3, "word": 5},
        {"page_number": 4, "word": 0}
    ]
    reading_loc.current_jump = 1  # Set current position to the second item
    reading_loc.save()

    response = client.post(reverse('jump_forward'), {
        'book-code': book.code,
    })

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['page_number'] == 3
    assert data['word'] == 5

    # Verify that the database was updated
    reading_loc.refresh_from_db()
    assert reading_loc.page_number == 3
    assert reading_loc.word == 5
    assert reading_loc.current_jump == 2


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_jump_back_view_successful(client, user, book):
    client.force_login(user)

    # Create a single ReadingLoc instance
    reading_loc = ReadingLoc.objects.create(user=user, book=book, page_number=3, word=5)

    # Simulate a jump history
    reading_loc.jump_history = [
        {"page_number": 1, "word": 0},
        {"page_number": 2, "word": 10},
        {"page_number": 3, "word": 5}
    ]
    reading_loc.current_jump = 2  # Set current position to the last item
    reading_loc.save()

    response = client.post(reverse('jump_back'), {
        'book-code': book.code,
    })

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['page_number'] == 2
    assert data['word'] == 10

    # Verify that the database was updated
    reading_loc.refresh_from_db()
    assert reading_loc.page_number == 2
    assert reading_loc.word == 10
    assert reading_loc.current_jump == 1


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_get_jump_status_view(client, user, book):
    client.force_login(user)

    # Create a single ReadingLoc instance
    reading_loc = ReadingLoc.objects.create(
        user=user,
        book=book,
        page_number=2,
        word=5,
        jump_history=[
            {"page_number": 1, "word": 0},
            {"page_number": 2, "word": 5},
            {"page_number": 3, "word": 10}
        ],
        current_jump=1  # Set current position to the middle of the history
    )

    response = client.get(reverse('get_jump_status'), {
        'book-code': book.code,
    })

    assert response.status_code == 200
    data = response.json()
    assert 'is_first_jump' in data
    assert 'is_last_jump' in data
    assert data['is_first_jump'] == False
    assert data['is_last_jump'] == False

    # Test first jump
    reading_loc.current_jump = 0
    reading_loc.save()
    response = client.get(reverse('get_jump_status'), {'book-code': book.code})
    data = response.json()
    assert data['is_first_jump'] == True
    assert data['is_last_jump'] == False

    # Test last jump
    reading_loc.current_jump = 2
    reading_loc.save()
    response = client.get(reverse('get_jump_status'), {'book-code': book.code})
    data = response.json()
    assert data['is_first_jump'] == False
    assert data['is_last_jump'] == True


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_reader_access_denied(client, book):
    # Assuming another_user does not have access to the book
    another_user = get_user_model().objects.create_user('another_user', 'another@example.com', 'password')
    client.force_login(another_user)
    response = client.get(reverse('reader'), {'book-code': book.code})

    assert response.status_code == 403


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