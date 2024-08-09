import allure
import pytest
from django.urls import reverse
from lexiflux.models import ReadingLoc
from pytest_django.asserts import assertTemplateUsed


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_reader_view_redirect_unauthenticated_user(client):
    response = client.get(reverse('reader') + f'?book-code=wrong-code')
    assert response.status_code == 302  # Expecting a redirect to login or another page


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_reader_view_renders_for_authenticated_user(client, user, book):
    client.force_login(user)
    response = client.get(reverse('reader') + f'?book-code={book.code}')
    assert response.status_code == 200
    assert book.title in response.content.decode()
    assert 'id="book-page-scroller"' in response.content.decode()
    assert '&#8592;' in response.content.decode()  # Left arrow


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_reader_view_redirects_to_latest_book_when_book_code_is_none(client, user, book):
    client.force_login(user)

    ReadingLoc.objects.create(user=user, book=book, page_number=1, word=1)
    response = client.get(reverse('reader'))

    assert response.status_code == 200
    assertTemplateUsed(response, 'reader.html')

    assert book.title in response.content.decode()


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_reader_view_loads_default_when_no_books_read_and_book_code_is_none(client, user):
    client.force_login(user)
    response = client.get(reverse('reader'))
    assert response.status_code == 302
    assert response.url == reverse('library')
