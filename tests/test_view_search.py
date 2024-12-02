import allure
import pytest
from django.urls import reverse


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_search_functionality_basic(client, approved_user, book):
    client.force_login(approved_user)

    # Create test page with content
    book.pages.all().delete()
    test_content = "This is test content with searchable words"
    book.pages.create(
        number=1,
        content=test_content,
        normalized_content=test_content.lower(),
        word_slices=[(0, 4), (5, 7), (8, 12), (13, 20), (21, 25), (26, 36), (37, 42)]
    )

    # Test basic search
    response = client.post(reverse('search'), {
        'book-code': book.code,
        'searchInput': 'test',
        'start_page': 1
    })

    assert response.status_code == 200
    content = response.content.decode()

    # Check for expected elements in response
    assert '<span class="bg-warning">test</span>' in content  # Table header
    assert '<td>1</td>' in content  # Page number
    assert '<span class="bg-warning">test</span>' in content  # Highlighted match


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_search_too_short_term(client, approved_user, book):
    client.force_login(approved_user)

    response = client.post(reverse('search'), {
        'book-code': book.code,
        'searchInput': 'te',
        'start_page': 1
    })

    assert response.status_code == 200
    content = response.content.decode()
    assert 'No results found' in content


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_search_whole_words_only(client, approved_user, book):
    client.force_login(approved_user)

    book.pages.all().delete()
    test_content = "The test is here. Some random words fill testing now. More words around tested case. Last line contains tests end."
    book.pages.create(
        number=1,
        content=test_content,
        normalized_content=test_content.lower(),
        word_slices=[(0, 3), (4, 8), (9, 11), (12, 16), (17, 21), (22, 27), (28, 32), (33, 40), (41, 44), (45, 49),
                     (50, 55), (56, 62), (63, 68), (69, 73), (74, 78), (79, 84), (85, 88)]
    )

    # Search with whole words off
    response = client.post(reverse('search'), {
        'book-code': book.code,
        'searchInput': 'test',
        'start_page': 1
    })
    content = response.content.decode()
    assert response.status_code == 200
    assert content.count('bg-warning') == 4

    # Search with whole words on
    response = client.post(reverse('search'), {
        'book-code': book.code,
        'searchInput': 'test',
        'start_page': 1,
        'whole-words': 'on'
    })
    content = response.content.decode()
    assert response.status_code == 200
    assert content.count('bg-warning') == 1  # Should only find exact "test"


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_search_from_current_page(client, approved_user, book):
    client.force_login(approved_user)

    book.pages.all().delete()
    # Create multiple pages with content
    book.pages.create(
        number=1,
        content="First test page",
        normalized_content="first test page",
        word_slices=[(0, 5), (6, 10), (11, 15)]
    )
    book.pages.create(
        number=2,
        content="Second test page",
        normalized_content="second test page",
        word_slices=[(0, 6), (7, 11), (12, 16)]
    )

    # Search from page 1
    response = client.post(reverse('search'), {
        'book-code': book.code,
        'searchInput': 'test',
        'start_page': 1
    })
    content = response.content.decode()
    assert '<td>1</td>' in content
    assert '<td>2</td>' in content

    # Search from page 2
    response = client.post(reverse('search'), {
        'book-code': book.code,
        'searchInput': 'test',
        'start_page': 2
    })
    content = response.content.decode()
    assert '<td>1</td>' not in content
    assert '<td>2</td>' in content


@allure.epic('Pages endpoints')
@allure.feature('Reader')
@pytest.mark.django_db
def test_search_pagination(client, approved_user, book):
    client.force_login(approved_user)

    book.pages.all().delete()
    # Create more pages than MAX_SEARCH_RESULTS
    for i in range(1, 22):  # Creating 21 pages
        book.pages.create(
            number=i,
            content=f"Test content page {i}",
            normalized_content=f"test content page {i}",
            word_slices=[(0, 4), (5, 12), (13, 17), (18, 20)]
        )

    # Initial search
    response = client.post(reverse('search'), {
        'book-code': book.code,
        'searchInput': 'test',
        'start_page': 1
    })
    content = response.content.decode()

    assert response.status_code == 200
    assert content.count('<tr') == 21  # 20 results + 1 spinner row
    assert 'spinner-border' in content

    # Load next page
    response = client.post(reverse('search'), {
        'book-code': book.code,
        'searchInput': 'test',
        'start_page': 21
    })
    content = response.content.decode()

    assert response.status_code == 200
    assert '<td>21</td>' in content