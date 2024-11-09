import json
from unittest.mock import patch, MagicMock

import allure
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile, TemporaryUploadedFile
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from lexiflux.models import Book, Author, Language


@allure.epic('Pages endpoints')
@allure.story('Library')
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


@allure.epic('Pages endpoints')
@allure.story('Library')
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


@allure.epic('Pages endpoints')
@allure.story('Library')
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


@allure.epic('Pages endpoints')
@allure.story('Book Import')
@pytest.mark.django_db
class TestImportBook:
    def test_import_book_not_post(self, client, approved_user):
        client.force_login(approved_user)
        response = client.get(reverse('import_book'))
        assert response.status_code == 405
        assert json.loads(response.content)['error'] == 'Invalid request method'

    def test_import_book_no_file(self, client, approved_user):
        client.force_login(approved_user)
        response = client.post(reverse('import_book'))
        assert response.status_code == 400
        assert json.loads(response.content)['error'] == 'No file provided'

    def test_import_book_unsupported_format(self, client, approved_user):
        client.force_login(approved_user)
        file = SimpleUploadedFile('test.pdf', b'file content', content_type='application/pdf')
        response = client.post(reverse('import_book'), {'file': file})
        assert response.status_code == 400
        assert json.loads(response.content)['error'] == 'Unsupported file format'

    @pytest.mark.parametrize('file_ext,loader_class', [
        ('txt', 'BookLoaderPlainText'),
        ('html', 'BookLoaderHtml'),
        ('epub', 'BookLoaderEpub'),
    ])
    def test_import_book_success_simple_file(self, client, approved_user, book, file_ext, loader_class):
        client.force_login(approved_user)

        # Create test file
        file = SimpleUploadedFile(
            f'test.{file_ext}',
            b'file content',
            content_type=f'text/{file_ext}'
        )

        with patch(f'lexiflux.views.library_views.{loader_class}') as MockLoader:
            mock_processor = MagicMock()
            mock_processor.create.return_value = book
            MockLoader.return_value = mock_processor

            response = client.post(reverse('import_book'), {'file': file})

        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['id'] == book.id
        assert response_data['title'] == book.title
        assert response_data['author'] == book.author.name
        assert response_data['language'] == book.language.google_code

    def test_import_book_with_temporary_file(self, client, approved_user, book):
        client.force_login(approved_user)

        # Mock TemporaryUploadedFile
        mock_temp_file = MagicMock(spec=TemporaryUploadedFile)
        mock_temp_file.name = 'test.txt'
        mock_temp_file.temporary_file_path.return_value = '/tmp/test.txt'

        with patch('lexiflux.views.library_views.BookLoaderPlainText') as MockLoader:
            mock_processor = MagicMock()
            mock_processor.create.return_value = book
            MockLoader.return_value = mock_processor

            with patch('django.core.files.uploadhandler.TemporaryFileUploadHandler.new_file',
                       return_value=mock_temp_file):
                response = client.post(
                    reverse('import_book'),
                    {'file': SimpleUploadedFile('test.txt', b'content')}
                )

        assert response.status_code == 200
        response_data = json.loads(response.content)
        print(response_data)
        assert response_data['id'] == book.id
        assert response_data['title'] == book.title

    def test_import_book_error_handling(self, client, approved_user):
        client.force_login(approved_user)
        file = SimpleUploadedFile('test.txt', b'file content', content_type='text/plain')

        with patch('lexiflux.views.library_views.BookLoaderPlainText') as MockLoader:
            MockLoader.side_effect = Exception('Test error')
            response = client.post(reverse('import_book'), {'file': file})

        assert response.status_code == 500
        assert json.loads(response.content)['error'] == 'Test error'


@allure.epic('Pages endpoints')
@allure.story('Book Details')
@pytest.mark.django_db
class TestBookDetailView:
    def test_get_book_details_not_found(self, client, approved_user):
        client.force_login(approved_user)
        response = client.get(reverse('book_detail', kwargs={'book_id': 999}))
        assert response.status_code == 404
        assert json.loads(response.content)['error'] == 'Book not found'

    def test_get_book_details_success(self, client, approved_user, book):
        client.force_login(approved_user)
        response = client.get(reverse('book_detail', kwargs={'book_id': book.id}))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['id'] == book.id
        assert data['title'] == book.title
        assert data['author'] == book.author.name
        assert data['language'] == book.language.google_code
        assert data['code'] == book.code

    def test_update_book_not_found(self, client, approved_user):
        client.force_login(approved_user)
        response = client.put(
            reverse('book_detail', kwargs={'book_id': 999}),
            data=json.dumps({'title': 'New Title'}),
            content_type='application/json'
        )
        assert response.status_code == 404
        assert json.loads(response.content)['error'] == 'Book not found'

    def test_update_book_success(self, client, approved_user, book, language):
        client.force_login(approved_user)
        new_data = {
            'title': 'Updated Title',
            'author': 'New Author',
            'language': language.google_code
        }

        response = client.put(
            reverse('book_detail', kwargs={'book_id': book.id}),
            data=json.dumps(new_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['title'] == 'Updated Title'
        assert data['author'] == 'New Author'
        assert data['language'] == language.google_code

        # Verify database was updated
        book.refresh_from_db()
        assert book.title == 'Updated Title'
        assert book.author.name == 'New Author'
        assert book.language.google_code == language.google_code

    def test_delete_book_not_found(self, client, approved_user):
        client.force_login(approved_user)
        response = client.delete(reverse('book_detail', kwargs={'book_id': 999}))
        assert response.status_code == 404
        assert json.loads(response.content)['error'] == 'Book not found'

    def test_delete_book_unauthorized(self, client, book):
        # Create and login as another user who doesn't own the book
        other_user = get_user_model().objects.create_user(
            'otheruser',
            'other@example.com',
            'password123'
        )
        client.force_login(other_user)

        response = client.delete(reverse('book_detail', kwargs={'book_id': book.id}))
        assert response.status_code == 403
        assert json.loads(response.content)['error'] == "You don't have permission to delete this book"

        # Verify book still exists
        book.refresh_from_db()
        assert book.id is not None

    def test_delete_book_success(self, client, approved_user, book):
        client.force_login(approved_user)
        response = client.delete(reverse('book_detail', kwargs={'book_id': book.id}))
        assert response.status_code == 200
        assert json.loads(response.content)['success'] == 'Book deleted successfully'

        # Verify book was deleted
        assert not book._meta.model.objects.filter(id=book.id).exists()


@allure.epic('Pages endpoints')
@allure.story('Author Search')
@pytest.mark.django_db
class TestSearchAuthors:
    def test_search_authors_empty_query(self, client, approved_user, author):
        client.force_login(approved_user)
        response = client.get(reverse('search_authors'), {'q': ''})
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['authors'] == []
        assert data['has_more'] is False

    def test_search_authors_single_word(self, client, approved_user, author):
        # Use the existing author fixture and create one additional author
        get_user_model().objects.create_user('otheruser', 'other@example.com', 'password123')

        client.force_login(approved_user)
        response = client.get(reverse('search_authors'), {'q': author.name.split()[0]})

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['authors']) == 1
        assert data['authors'][0] == author.name
        assert data['has_more'] is False

    def test_search_authors_pagination(self, client, approved_user, author):
        # Create additional authors with similar names to test pagination
        base_name = author.name.split()[0]
        for i in range(100):  # Create enough authors to trigger pagination
            author._meta.model.objects.create(name=f"{base_name} {i}")

        client.force_login(approved_user)
        response = client.get(reverse('search_authors'), {'q': base_name})

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['authors']) == 100
        assert data['has_more'] is True

    def test_search_authors_special_characters(self, client, approved_user, author):
        # Create authors with special characters in their names using the Author model
        Author.objects.create(name="Jean-Paul")
        Author.objects.create(name="St. John")

        client.force_login(approved_user)

        # Test hyphenated name
        response = client.get(reverse('search_authors'), {'q': 'Paul'})
        data = json.loads(response.content)
        assert 'Jean-Paul' in data['authors']

        # Test name with period
        response = client.get(reverse('search_authors'), {'q': 'John'})
        data = json.loads(response.content)
        assert 'St. John' in data['authors']
