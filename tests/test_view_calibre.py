"""Tests for Calibre integration views - Fixed version."""

import base64
import json
import tempfile
from unittest.mock import MagicMock, patch

import allure
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from lexiflux.models import Author, Book


@allure.epic("API endpoints")
@allure.story("Calibre Integration")
@pytest.mark.django_db
class TestCalibreHandshake:
    """Test Calibre device handshake endpoint."""

    def test_handshake_stage_1(self, client):
        """Test initial handshake stage."""
        response = client.get(reverse("calibre_handshake"), {"stage": "1"})

        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == 1
        assert data["device_name"] == "Lexiflux"
        assert data["device_version"] == "1.0.0"
        assert "epub" in data["preferred_formats"]
        assert data["can_stream_books"] is True
        assert data["can_receive_books"] is True
        assert data["password_required"] is False

    def test_handshake_stage_2(self, client):
        """Test connection confirmation stage."""
        response = client.get(reverse("calibre_handshake"), {"stage": "2"})

        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == 2
        assert data["device_name"] == "Lexiflux"
        assert data["status"] == "connected"
        assert "session_id" in data

    def test_handshake_invalid_stage(self, client):
        """Test invalid handshake stage."""
        response = client.get(reverse("calibre_handshake"), {"stage": "99"})

        assert response.status_code == 400
        data = response.json()
        assert "Invalid handshake stage" in data["error"]

    def test_handshake_default_stage(self, client):
        """Test handshake without stage parameter defaults to stage 1."""
        response = client.get(reverse("calibre_handshake"))

        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == 1


@allure.epic("API endpoints")
@allure.story("Calibre Integration")
@pytest.mark.django_db
class TestCalibreUploadBook:
    """Test Calibre book upload endpoint."""

    def test_upload_book_no_file(self, client):
        """Test upload without file."""
        # Mock the authentication to return a user email
        with patch("lexiflux.views.calibre_views._get_authenticated_user_email") as mock_auth:
            mock_auth.return_value = "test@example.com"

            response = client.post(reverse("calibre_upload_book"))

            assert response.status_code == 400
            data = response.json()
            assert "No file provided" in data["error"]

    def test_upload_book_no_auth(self, client):
        """Test upload without authentication returns 401."""
        epub_content = b"mock epub file content"
        uploaded_file = SimpleUploadedFile(
            "test_book.epub", epub_content, content_type="application/epub+zip"
        )

        # No auth mock - should fail
        response = client.post(
            reverse("calibre_upload_book"),
            {"book_file": uploaded_file},
        )

        assert response.status_code == 401
        data = response.json()
        assert "Authentication required" in data["error"]

    def test_upload_book_with_token(self, client, book):
        """Test book upload with token authentication."""
        # Create test EPUB file
        epub_content = b"mock epub file content"
        uploaded_file = SimpleUploadedFile(
            "test_book.epub", epub_content, content_type="application/epub+zip"
        )

        metadata = {"title": "Test Book from Calibre", "authors": ["Test Author"], "language": "en"}

        with patch("lexiflux.views.calibre_views._import_book_file") as mock_import:
            mock_import.return_value = book

            # Mock successful authentication
            with patch("lexiflux.views.calibre_views._get_authenticated_user_email") as mock_auth:
                mock_auth.return_value = "test@example.com"

                response = client.post(
                    reverse("calibre_upload_book"),
                    {"book_file": uploaded_file, "metadata": json.dumps(metadata)},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["book_id"] == book.id
        assert book.title in data["message"]

    def test_upload_book_auth_required(self, client):
        """Test book upload requires authentication."""
        epub_content = b"mock epub file content"
        uploaded_file = SimpleUploadedFile(
            "test_book.epub", epub_content, content_type="application/epub+zip"
        )

        # Don't mock auth - should return 401
        response = client.post(reverse("calibre_upload_book"), {"book_file": uploaded_file})

        assert response.status_code == 401
        data = response.json()
        assert "Authentication required" in data["error"]

    def test_upload_book_authenticated_user(self, client, approved_user, book):
        """Test book upload with authenticated user."""
        epub_content = b"mock epub file content"
        uploaded_file = SimpleUploadedFile(
            "test_book.epub", epub_content, content_type="application/epub+zip"
        )

        metadata = {"title": "Test Book from Calibre", "authors": ["Test Author"], "language": "en"}

        with patch("lexiflux.views.calibre_views._import_book_file") as mock_import:
            mock_import.return_value = book

            # Mock token authentication
            with patch("lexiflux.views.calibre_views._get_authenticated_user_email") as mock_auth:
                mock_auth.return_value = approved_user.email

                response = client.post(
                    reverse("calibre_upload_book"),
                    {"book_file": uploaded_file, "metadata": json.dumps(metadata)},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_upload_book_json_format(self, client, book):
        """Test JSON-based book upload."""
        # Create base64 encoded content
        epub_content = b"mock epub file content"
        encoded_content = base64.b64encode(epub_content).decode("utf-8")

        json_data = {
            "opcode": "UPLOAD_BOOK",
            "book_data": {"filename": "test_book.epub", "content": encoded_content},
            "metadata": {"title": "Test JSON Book", "authors": ["JSON Author"], "language": "en"},
        }

        with patch("lexiflux.views.calibre_views._import_book_from_path") as mock_import:
            mock_import.return_value = book

            # Mock authentication
            with patch("lexiflux.views.calibre_views._get_authenticated_user_email") as mock_auth:
                mock_auth.return_value = "test@example.com"

                response = client.post(
                    reverse("calibre_upload_book"),
                    data=json.dumps(json_data),
                    content_type="application/json",
                )

        assert response.status_code == 200
        data = response.json()
        assert data["opcode"] == "UPLOAD_BOOK_RESPONSE"
        assert data["status"] == "success"

    def test_upload_book_json_unknown_opcode(self, client):
        """Test JSON upload with unknown opcode."""
        json_data = {"opcode": "UNKNOWN_OPERATION", "data": {}}

        # Mock authentication
        with patch("lexiflux.views.calibre_views._get_authenticated_user_email") as mock_auth:
            mock_auth.return_value = "test@example.com"

            response = client.post(
                reverse("calibre_upload_book"),
                data=json.dumps(json_data),
                content_type="application/json",
            )

        assert response.status_code == 400
        data = response.json()
        assert "Unknown opcode" in data["error"]

    def test_upload_book_invalid_json(self, client):
        """Test upload with invalid JSON data."""
        # Mock authentication
        with patch("lexiflux.views.calibre_views._get_authenticated_user_email") as mock_auth:
            mock_auth.return_value = "test@example.com"

            response = client.post(
                reverse("calibre_upload_book"), data="invalid json", content_type="application/json"
            )

            assert response.status_code == 400
            data = response.json()
            assert "Invalid JSON" in data["error"]


@allure.epic("API endpoints")
@allure.story("Calibre Integration")
@pytest.mark.django_db
class TestCalibreStatus:
    """Test Calibre device status endpoint."""

    def test_status_endpoint(self, client, book, approved_user):
        """Test status endpoint returns correct information."""
        response = client.get(reverse("calibre_status"))

        assert response.status_code == 200
        data = response.json()
        assert data["device_name"] == "Lexiflux"
        assert data["device_version"] == "1.0.0"
        assert data["status"] == "ready"
        assert data["book_count"] >= 1  # At least the test book
        assert data["user_count"] >= 1  # At least the test user
        assert "epub" in data["preferred_formats"]
        assert "timestamp" in data


@allure.epic("API endpoints")
@allure.story("Calibre Integration")
@pytest.mark.django_db
class TestCalibreBookImport:
    """Test Calibre book import functions."""

    @pytest.fixture
    def mock_epub_file(self):
        """Create a mock EPUB file."""
        return SimpleUploadedFile(
            "test.epub", b"mock epub content", content_type="application/epub+zip"
        )

    @pytest.fixture
    def mock_html_file(self):
        """Create a mock HTML file."""
        return SimpleUploadedFile(
            "test.html", b"<html><body>Test content</body></html>", content_type="text/html"
        )

    @pytest.fixture
    def mock_txt_file(self):
        """Create a mock text file."""
        return SimpleUploadedFile("test.txt", b"Test text content", content_type="text/plain")

    @patch("lexiflux.views.calibre_views.BookLoaderEpub")
    def test_import_epub_file(self, MockLoader, mock_epub_file, approved_user):
        """Test importing EPUB file."""
        from lexiflux.views.calibre_views import _import_book_file

        metadata = {"title": "Test EPUB Book", "authors": ["Test Author"], "language": "en"}

        mock_book = MagicMock(spec=Book)
        mock_book.title = "Test EPUB Book"
        mock_book.save = MagicMock()

        mock_processor = MagicMock()
        mock_processor.create.return_value = mock_book
        MockLoader.return_value = mock_processor

        result = _import_book_file(mock_epub_file, "test.epub", metadata, approved_user.email)

        assert result == mock_book
        MockLoader.assert_called_once()
        mock_processor.create.assert_called_once_with(approved_user.email)

    @patch("lexiflux.views.calibre_views.BookLoaderHtml")
    def test_import_html_file(self, MockLoader, mock_html_file, approved_user):
        """Test importing HTML file."""
        from lexiflux.views.calibre_views import _import_book_file

        metadata = {"title": "Test HTML Book"}

        mock_book = MagicMock(spec=Book)
        mock_book.save = MagicMock()

        mock_processor = MagicMock()
        mock_processor.create.return_value = mock_book
        MockLoader.return_value = mock_processor

        result = _import_book_file(mock_html_file, "test.html", metadata, approved_user.email)

        assert result == mock_book
        MockLoader.assert_called_once()

    @patch("lexiflux.views.calibre_views.BookLoaderPlainText")
    def test_import_txt_file(self, MockLoader, mock_txt_file, approved_user):
        """Test importing text file."""
        from lexiflux.views.calibre_views import _import_book_file

        metadata = {"title": "Test Text Book"}

        mock_book = MagicMock(spec=Book)
        mock_book.save = MagicMock()

        mock_processor = MagicMock()
        mock_processor.create.return_value = mock_book
        MockLoader.return_value = mock_processor

        result = _import_book_file(mock_txt_file, "test.txt", metadata, approved_user.email)

        assert result == mock_book
        MockLoader.assert_called_once()

    def test_import_unsupported_format(self, approved_user):
        """Test importing unsupported file format."""
        from lexiflux.views.calibre_views import _import_book_file

        unsupported_file = SimpleUploadedFile(
            "test.pdf", b"pdf content", content_type="application/pdf"
        )

        with pytest.raises(ValueError, match="Unsupported file format"):
            _import_book_file(unsupported_file, "test.pdf", {}, approved_user.email)

    @patch("lexiflux.views.calibre_views.BookLoaderEpub")
    @patch("lexiflux.models.Author")
    def test_import_with_metadata_override(
        self, MockAuthor, MockLoader, mock_epub_file, approved_user, language
    ):
        """Test that Calibre metadata overrides book metadata."""
        from lexiflux.views.calibre_views import _import_book_file

        metadata = {
            "title": "Calibre Title",
            "authors": ["Calibre Author"],
            "language": language.google_code,
        }

        # Mock the Author model
        mock_author = MagicMock(spec=Author)
        mock_author.name = "Calibre Author"
        MockAuthor.objects.get_or_create.return_value = (mock_author, True)

        mock_book = MagicMock(spec=Book)
        mock_book.title = "Original Title"
        mock_book.author = None  # Will be set by the import function
        mock_book.save = MagicMock()

        mock_processor = MagicMock()
        mock_processor.create.return_value = mock_book
        MockLoader.return_value = mock_processor

        result = _import_book_file(mock_epub_file, "test.epub", metadata, approved_user.email)

        # Verify metadata was applied
        assert result.title == "Calibre Title"
        assert result.author == mock_author  # Now it's an Author object, not a string
        assert result.language == language

        # Verify Author.get_or_create was called
        MockAuthor.objects.get_or_create.assert_called_once_with(
            name="Calibre Author", defaults={"name": "Calibre Author"}
        )

    @patch("lexiflux.views.calibre_views.BookLoaderEpub")
    def test_import_from_path(self, MockLoader, approved_user):
        """Test importing book from file path."""
        from lexiflux.views.calibre_views import _import_book_from_path

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp_file:
            tmp_file.write(b"mock epub content")
            tmp_file.flush()

            metadata = {"title": "Path Test Book"}

            mock_book = MagicMock(spec=Book)
            mock_book.save = MagicMock()

            mock_processor = MagicMock()
            mock_processor.create.return_value = mock_book
            MockLoader.return_value = mock_processor

            result = _import_book_from_path(
                tmp_file.name, "test.epub", metadata, approved_user.email
            )

            assert result == mock_book
            MockLoader.assert_called_once_with(tmp_file.name, original_filename="test.epub")

    @patch("lexiflux.views.calibre_views.BookLoaderEpub")
    def test_import_with_unknown_language(self, MockLoader, mock_epub_file, approved_user, caplog):
        """Test importing with unknown language code."""
        from lexiflux.views.calibre_views import _import_book_file

        metadata = {"title": "Test Book", "language": "unknown_lang_code"}

        mock_book = MagicMock(spec=Book)
        mock_book.save = MagicMock()

        mock_processor = MagicMock()
        mock_processor.create.return_value = mock_book
        MockLoader.return_value = mock_processor

        _import_book_file(mock_epub_file, "test.epub", metadata, approved_user.email)

        # Check that warning was logged
        assert "Language unknown_lang_code not found in database" in caplog.text
