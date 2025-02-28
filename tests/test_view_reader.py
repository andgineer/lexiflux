import allure
import pytest
from bs4 import BeautifulSoup
from django.urls import reverse
from django.contrib.auth import get_user_model
from lexiflux.models import ReadingLoc, ReaderSettings, BookImage
from pytest_django.asserts import assertTemplateUsed


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_reader_view_redirect_unauthenticated_user(client):
    response = client.get(reverse("reader") + "?book-code=wrong-code")
    assert response.status_code == 302  # Expecting a redirect to login or another page


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_reader_view_renders_for_authenticated_user(client, user, book):
    client.force_login(user)
    response = client.get(reverse("reader") + f"?book-code={book.code}")
    assert response.status_code == 200
    assert book.title in response.content.decode()
    assert 'id="book-page-scroller"' in response.content.decode()
    assert "bi-caret-left-fill" in response.content.decode()


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_reader_view_redirects_to_latest_book_when_book_code_is_none(client, user, book):
    client.force_login(user)

    ReadingLoc.objects.create(user=user, book=book, page_number=1, word=1)
    response = client.get(reverse("reader"))

    assert response.status_code == 200
    assertTemplateUsed(response, "reader.html")

    assert book.title in response.content.decode()


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_reader_view_loads_default_when_no_books_read_and_book_code_is_none(client, user):
    client.force_login(user)
    response = client.get(reverse("reader"))
    assert response.status_code == 302
    assert response.url == reverse("library")


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_location_view_updates_reading_location_successfully(client, user, book):
    client.force_login(user)
    book_id = book.id
    page_number = 1
    top_word = 10

    response = client.post(
        reverse("location"),
        {"book-code": book.code, "book-page-number": page_number, "top-word": top_word},
    )

    assert response.status_code == 200, f"Failed to update reading location: {response.content}"
    assert ReadingLoc.objects.filter(
        user=user, book_id=book_id, page_number=page_number, word=top_word
    ).exists(), "Reading location should be updated in the database"


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_location_view_handles_invalid_parameters(client, user):
    client.force_login(user)

    # Intentionally omitting 'book-page-number' to trigger a 400 error
    response = client.post(reverse("location"), {"book-code": "invalid", "top-word": "not-an-int"})

    assert response.status_code == 400


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_location_view_enforces_access_control(client, user, book):
    # Create another user who does not have access to the book
    AnotherUser = get_user_model()
    another_user = AnotherUser.objects.create_user(
        username="another_user", password="67890", email="email"
    )
    client.force_login(another_user)

    response = client.post(
        reverse("location"), {"book-code": book.code, "book-page-number": 1, "top-word": 10}
    )

    assert response.status_code == 403, (
        f"User should not be able to update reading location for a book they don't have access to: {response.content}"
    )


@allure.epic("Pages endpoints")
@allure.feature("Reader")
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
        current_jump=0,
    )

    response = client.post(
        reverse("jump"), {"book-code": book.code, "book-page-number": 2, "top-word": 5}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify that the database was updated
    reading_loc = ReadingLoc.objects.get(user=user, book=book)
    assert reading_loc.page_number == 2
    assert reading_loc.word == 5
    assert reading_loc.current_jump == 1
    assert reading_loc.jump_history == [
        {"page_number": 1, "word": 0},
        {"page_number": 2, "word": 5},
    ]


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_jump_view_invalid_parameters(client, user):
    client.force_login(user)
    response = client.post(
        reverse("jump"),
        {"book-code": "invalid", "book-page-number": "not-a-number", "top-word": "not-a-number"},
    )

    assert response.status_code == 400


@allure.epic("Pages endpoints")
@allure.feature("Reader")
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
        {"page_number": 4, "word": 0},
    ]
    reading_loc.current_jump = 1  # Set current position to the second item
    reading_loc.save()

    response = client.post(
        reverse("jump_forward"),
        {
            "book-code": book.code,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["page_number"] == 3
    assert data["word"] == 5

    # Verify that the database was updated
    reading_loc.refresh_from_db()
    assert reading_loc.page_number == 3
    assert reading_loc.word == 5
    assert reading_loc.current_jump == 2


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_jump_back_view_successful(client, user, book):
    client.force_login(user)

    # Create a single ReadingLoc instance
    reading_loc = ReadingLoc.objects.create(user=user, book=book, page_number=3, word=5)

    # Simulate a jump history
    reading_loc.jump_history = [
        {"page_number": 1, "word": 0},
        {"page_number": 2, "word": 10},
        {"page_number": 3, "word": 5},
    ]
    reading_loc.current_jump = 2  # Set current position to the last item
    reading_loc.save()

    response = client.post(
        reverse("jump_back"),
        {
            "book-code": book.code,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["page_number"] == 2
    assert data["word"] == 10

    # Verify that the database was updated
    reading_loc.refresh_from_db()
    assert reading_loc.page_number == 2
    assert reading_loc.word == 10
    assert reading_loc.current_jump == 1


@allure.epic("Pages endpoints")
@allure.feature("Reader")
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
            {"page_number": 3, "word": 10},
        ],
        current_jump=1,  # Set current position to the middle of the history
    )

    response = client.get(
        reverse("get_jump_status"),
        {
            "book-code": book.code,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "is_first_jump" in data
    assert "is_last_jump" in data
    assert data["is_first_jump"] == False
    assert data["is_last_jump"] == False

    # Test first jump
    reading_loc.current_jump = 0
    reading_loc.save()
    response = client.get(reverse("get_jump_status"), {"book-code": book.code})
    data = response.json()
    assert data["is_first_jump"] == True
    assert data["is_last_jump"] == False

    # Test last jump
    reading_loc.current_jump = 2
    reading_loc.save()
    response = client.get(reverse("get_jump_status"), {"book-code": book.code})
    data = response.json()
    assert data["is_first_jump"] == False
    assert data["is_last_jump"] == True


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_reader_access_denied(client, book):
    # Assuming another_user does not have access to the book
    another_user = get_user_model().objects.create_user(
        "another_user", "another@example.com", "password"
    )
    client.force_login(another_user)
    response = client.get(reverse("reader"), {"book-code": book.code})

    assert response.status_code == 403


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_normalize_path_removes_dots_and_slashes():
    from lexiflux.views.reader_views import normalize_path

    test_cases = [
        ("../path/to/file.jpg", "path/to/file.jpg"),
        ("path//to///file.jpg", "path/to/file.jpg"),
        ("./path/to/file.jpg", "path/to/file.jpg"),
        ("path/../../file.jpg", "file.jpg"),
        ("path/%2E%2E/file.jpg", "file.jpg"),  # URL encoded ..
        ("path/../to/./file.jpg", "to/file.jpg"),
    ]

    for input_path, expected in test_cases:
        assert normalize_path(input_path) == expected


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_set_sources_replaces_image_sources(book, client):
    from lexiflux.views.reader_views import rewire_epub_references

    # Create a test BookImage
    test_image = BookImage.objects.create(
        book=book, filename="test.jpg", image_data=b"fake_image_data", content_type="image/jpeg"
    )

    test_html = '<img src="test.jpg"><img src="../images/test.jpg">'
    processed_html = rewire_epub_references(test_html, book)

    soup = BeautifulSoup(processed_html, "html.parser")
    images = soup.find_all("img")

    expected_url = reverse(
        "serve_book_image", kwargs={"book_code": book.code, "image_filename": test_image.filename}
    )

    assert all(img["src"] == expected_url for img in images)


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_set_sources_handles_internal_links(book):
    from lexiflux.views.reader_views import rewire_epub_references

    test_html = """
        <a href="#chapter1">Anchor Link</a>
        <a href="chapter2.html">Internal Page</a>
        <a href="../folder/page.html">Internal Path</a>
        <a href="http://external.com">External Link</a>
        <a href="https://another.com">Another External</a>
    """
    processed_html = rewire_epub_references(test_html, book)
    soup = BeautifulSoup(processed_html, "html.parser")

    links = soup.find_all("a")

    # Internal links should be converted to javascript:void(0); with original href stored in data-href
    internal_links = [
        ("Anchor Link", "#chapter1"),
        ("Internal Page", "chapter2.html"),
        ("Internal Path", "folder/page.html"),  # normalized path
    ]
    for text, original_href in internal_links:
        link = soup.find("a", string=text)
        assert link["href"] == "javascript:void(0);"
        assert link["data-href"] == original_href

    # External links (with protocol) should remain unchanged
    external_links = [
        ("External Link", "http://external.com"),
        ("Another External", "https://another.com"),
    ]
    for text, original_href in external_links:
        link = soup.find("a", string=text)
        assert link["href"] == original_href
        assert "data-href" not in link.attrs


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_serve_book_image_success(client, book, approved_user):
    # Create a test image
    test_image = BookImage.objects.create(
        book=book, filename="test.jpg", image_data=b"fake_image_data", content_type="image/jpeg"
    )

    client.force_login(approved_user)
    response = client.get(
        reverse(
            "serve_book_image",
            kwargs={"book_code": book.code, "image_filename": test_image.filename},
        )
    )

    assert response.status_code == 200
    assert response.content == b"fake_image_data"
    assert response["Content-Type"] == "image/jpeg"


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_serve_book_image_unauthorized(client, book):
    # Create another user who does not have access to the book
    AnotherUser = get_user_model()
    another_user = AnotherUser.objects.create_user(
        username="another_user", password="67890", email="email"
    )
    client.force_login(another_user)

    # Create a test image
    test_image = BookImage.objects.create(
        book=book, filename="test.jpg", image_data=b"fake_image_data", content_type="image/jpeg"
    )

    response = client.get(
        reverse(
            "serve_book_image",
            kwargs={"book_code": book.code, "image_filename": test_image.filename},
        )
    )

    assert response.status_code == 403


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_link_click_success(client, approved_user, book):
    client.force_login(approved_user)

    # Update book's anchor_map with test data
    book.anchor_map = {"#chapter1": {"page": 2, "word": 5}}
    book.save()

    response = client.post(reverse("link_click"), {"book-code": book.code, "link": "#chapter1"})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["page_number"] == 2
    assert data["word"] == 5


@allure.epic("Pages endpoints")
@allure.feature("Reader")
@pytest.mark.django_db
def test_save_reader_settings_success(client, approved_user, book):
    client.force_login(approved_user)

    settings_data = {
        "book_code": book.code,
        "font_family": "Arial, sans-serif",
        "font_size": "16px",
    }

    response = client.post(reverse("save_reader_settings"), settings_data)

    assert response.status_code == 200

    # Verify settings were saved
    saved_settings = ReaderSettings.objects.get(user=approved_user, book=book)
    assert saved_settings.font_family == "Arial, sans-serif"
    assert saved_settings.font_size == "16px"
