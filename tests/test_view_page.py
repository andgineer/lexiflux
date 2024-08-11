import allure
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache as django_cache

from lexiflux.models import Author, Language, Book, BookPage
from lexiflux.views.reader_views import render_page


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_page_view_retrieves_book_page_successfully(client, user, book):
    client.force_login(user)
    page_number = 1
    response = client.get(reverse('page') + f'?book-code={book.code}&book-page-number={page_number}')

    assert response.status_code == 200
    assert 'html' in response.json()
    assert 'data' in response.json()
    assert response.json()['data']['bookCode'] == book.code
    assert response.json()['data']['pageNumber'] == page_number


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_page_view_handles_nonexistent_book_page(client, user, book):
    client.force_login(user)
    non_existent_page_number = 100
    response = client.get(reverse('page') + f'?book-code={book.code}&book-page-number={non_existent_page_number}')

    assert response.status_code == 500
    print(response.content.decode())
    assert "error: Page" in response.content.decode()


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_page_view_respects_access_control(client, user, book):
    # Assuming the setup creates a book not shared with or owned by 'another_user'
    another_user = get_user_model().objects.create_user(username='another_user', password='67890', email="email")
    client.force_login(another_user)

    page_number = 1
    response = client.get(reverse('page') + f'?book-code={book.code}&book-page-number={page_number}')

    # Expect a 403 Forbidden response since 'another_user' should not have access to 'book'
    assert response.status_code == 403


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.parametrize("content,expected_output", [
    (
        "Hello world <br/> New line",
        '<span class="word" id="word-0">Hello</span> <span class="word" id="word-1">world</span> <br/> <span class="word" id="word-2">New</span> <span class="word" id="word-3">line</span>'
    ),
    (
        "<br/>",
        '<br/>'
    ),
    (
        "SingleWord",
        '<span class="word" id="word-0">SingleWord</span>'
    ),
])
@pytest.mark.django_db
def test_render_page(content, expected_output, book):
    page = BookPage.objects.create(
        book=book,
        number=book.pages.count() + 1,  # Use a new page number
        content=content
    )
    assert render_page(page) == expected_output
