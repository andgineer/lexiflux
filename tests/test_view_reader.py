import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_reader_view_redirect_unauthenticated_user(client):
    # Use 'read_the_book' for the URL name that includes 'book_code'
    response = client.get(reverse('read_the_book', kwargs={'book_code': 'some-book-code'}))
    assert response.status_code == 302  # Expecting a redirect to login or another page


@pytest.mark.django_db
def test_reader_view_renders_for_authenticated_user(client, user, book):
    client.force_login(user)
    # Again, using 'read_the_book' for the URL name with 'book_code'
    response = client.get(reverse('read_the_book', kwargs={'book_code': book.code}))
    assert response.status_code == 200
    assert book.title in response.content.decode()
    assert 'id="book-page-scroller"' in response.content.decode()
    assert '&#8592;' in response.content.decode()  # Left arrow