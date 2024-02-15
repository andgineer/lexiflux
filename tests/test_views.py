import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client
from lexiflux.models import ReadingLoc

@pytest.mark.django_db
def test_location_view_updates_reading_location_successfully(client, user, book):
    client.force_login(user)
    book_id = book.id
    page_number = 1
    top_word = 10

    response = client.get(reverse('location'), {
        'book-id': book_id,
        'book-page-num': page_number,
        'top-word': top_word
    })

    assert response.status_code == 200
    assert ReadingLoc.objects.filter(
        user=user,
        book_id=book_id,
        page_number=page_number,
        word=top_word
    ).exists(), "Reading location should be updated in the database"


@pytest.mark.django_db
def test_location_view_handles_invalid_parameters(client, user):
    client.force_login(user)

    # Intentionally omitting 'book-page-num' to trigger a 400 error
    response = client.get(reverse('location'), {
        'book-id': 'invalid',
        'top-word': 'not-an-int'
    })

    assert response.status_code == 400


@pytest.mark.django_db
def test_location_view_enforces_access_control(client, user, book):
    # Create another user who does not have access to the book
    AnotherUser = get_user_model()
    another_user = AnotherUser.objects.create_user(username='another_user', password='67890', email="email")
    client.force_login(another_user)

    response = client.get(reverse('location'), {
        'book-id': book.id,
        'book-page-num': 1,
        'top-word': 10
    })

    assert response.status_code == 403, "User should not be able to update reading location for a book they don't have access to"
