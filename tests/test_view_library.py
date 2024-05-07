import allure
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import User
from pytest_django.asserts import assertTemplateUsed

from lexiflux.models import Book, Author, Language


@allure.epic('View: Library')
@pytest.mark.django_db
def test_library_view_for_regular_user(client, user, book):
    # Assuming 'user' fixture creates a regular user and 'book' fixture creates a book owned by the user
    client.force_login(user)

    another_user = get_user_model().objects.create_user('another_user', password='12345', email="email")
    shared_book = Book.objects.create(title="Shared Book", author=book.author, language=book.language,
                                      code='shared-book-code', owner=another_user, public=False)
    shared_book.shared_with.add(user)
    Book.objects.create(title="Public Book", author=book.author, language=book.language, code='public-book-code',
                        owner=another_user, public=True)
    Book.objects.create(title="Private Book", author=book.author, language=book.language, code='private-book-code',
                        owner=another_user, public=False)

    response = client.get(reverse('library'))

    assert response.status_code == 200
    assert len(response.context['books']) == 3  # Expecting 3 books: owned, shared, and public
    assertTemplateUsed(response, 'library.html')


@allure.epic('View: Library')
@pytest.mark.django_db
def test_library_view_for_superuser(client, book):
    # Create a separate superuser who does not own any book
    superuser = get_user_model().objects.create_superuser('superuser', 'superuser@example.com', 'superpassword')
    client.force_login(superuser)

    another_user = get_user_model().objects.create_user('another_user', 'another@example.com', 'password123')
    author = Author.objects.get(name="Lewis Carroll")  # Assuming an author already exists
    language = Language.objects.get(name="English")  # Assuming a language already exists

    Book.objects.create(title="Another Book", author=author, language=language, code='another-book-code', owner=another_user, public=False)
    Book.objects.create(title="Public Book", author=author, language=language, code='public-book-code', public=True)

    response = client.get(reverse('library'))

    # Verify that the superuser sees all books, regardless of ownership or public status
    assert response.status_code == 200
    books = response.context['books']
    assert len(books) >= 3, "Superuser should see all books in the library"


@allure.epic('View: Library')
@pytest.mark.django_db
def test_library_view_pagination(client, user, author, book):
    client.force_login(user)

    # Ensure you have enough books to test pagination
    # Assuming each test runs in isolation with a clean database
    language = Language.objects.get(name="English")  # Assuming this exists
    total_books = 15  # Example: Create 15 books to ensure pagination
    for i in range(2, total_books + 1):  # Starting from 2 because one book is already created by the fixture
        Book.objects.create(
            title=f"Book {i}",
            author=author,
            language=language,
            code=f'book-code-{i}',
            owner=user if i % 2 == 0 else None,  # Some owned by the user, some not to vary the setup
            public=True if i % 2 != 0 else False  # Alternate between public and private
        )

    response = client.get(reverse('library'), {'page': 2})

    # Verify the response and pagination
    assert response.status_code == 200
    assert 'books' in response.context
    books_page = response.context['books']
    assert books_page.number == 2, "Expected to be on the second page"

