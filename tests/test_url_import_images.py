"""Tests for URL import image functionality."""

from unittest.mock import patch, MagicMock
from django.test import TestCase

from lexiflux.ebook.book_loader_url import BookLoaderURL
from lexiflux.models import Language, Author


class TestURLImportImages(TestCase):
    """Test image downloading and processing in URL imports."""

    def setUp(self):
        """Set up test data."""
        self.language, _ = Language.objects.get_or_create(
            name="English", defaults={"google_code": "en"}
        )
        self.author, _ = Author.objects.get_or_create(name="Test Author")

    @patch("requests.get")
    def test_image_preparation_and_mapping(self, mock_requests):
        """Test that images are properly identified and mapped for download."""
        # Mock the main page request
        mock_main_response = MagicMock()
        mock_main_response.text = """
        <html>
        <body>
            <h1>Test Article</h1>
            <p>Some content</p>
            <img src="image1.jpg" alt="Test image 1">
            <img src="/path/to/image2.png" alt="Test image 2">
            <img src="https://example.com/image3.gif" alt="Test image 3">
        </body>
        </html>
        """
        mock_main_response.raise_for_status.return_value = None

        # Configure requests.get to return different responses based on URL
        def mock_get_side_effect(url, **kwargs):
            if url == "https://example.com/test-page":
                return mock_main_response
            else:
                # For image requests
                mock_img_response = MagicMock()
                mock_img_response.content = b"fake_image_data"
                mock_img_response.headers = {"content-type": "image/jpeg"}
                mock_img_response.raise_for_status.return_value = None
                return mock_img_response

        mock_requests.side_effect = mock_get_side_effect

        loader = BookLoaderURL("https://example.com/test-page")

        # Mock the text processing that normally happens in load_text
        loader.text = mock_main_response.text
        loader.html_content = mock_main_response.text

        # Test image preparation
        loader._prepare_images_for_download()

        # Should have identified 3 images
        self.assertEqual(len(loader.image_mapping), 3)

        # Check that relative URLs are converted to absolute
        expected_urls = {
            "image1.jpg": "https://example.com/image1.jpg",
            "/path/to/image2.png": "https://example.com/path/to/image2.png",
            "https://example.com/image3.gif": "https://example.com/image3.gif",
        }

        for original_src, image_info in loader.image_mapping.items():
            self.assertIn(original_src, expected_urls)
            self.assertEqual(image_info["absolute_url"], expected_urls[original_src])
            self.assertIsNotNone(image_info["filename"])

    @patch("requests.get")
    @patch("lexiflux.ebook.book_loader_url.BookLoaderURL._download_and_save_images")
    @patch("lexiflux.ebook.book_loader_url.BookLoaderURL._prepare_images_for_download")
    def test_create_with_images(self, mock_prepare, mock_download, mock_requests):
        """Test that create method calls image processing methods."""
        # Mock the main page request
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test</h1></body></html>"
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        loader = BookLoaderURL("https://example.com/test-page")

        # Mock required attributes and methods
        loader.text = "<html><body><h1>Test</h1></body></html>"
        loader.html_content = loader.text
        loader.anchor_map = {}

        with patch.object(loader, "detect_meta") as mock_detect_meta:
            mock_detect_meta.return_value = (
                {"title": "Test Book", "author": "Test Author", "language": "English"},
                0,
                100,
            )

            with patch.object(loader, "pages") as mock_pages:
                mock_pages.return_value = ["<p>Test content</p>"]

                book = loader.create(owner_email=None)

                # Verify image processing methods were called
                mock_prepare.assert_called_once()
                mock_download.assert_called_once_with(book)

    @patch("requests.get")
    def test_download_image_success(self, mock_requests):
        """Test successful image download."""
        # Mock image response
        mock_response = MagicMock()
        mock_response.content = b"fake_image_data_that_is_long_enough"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        loader = BookLoaderURL("https://example.com/test-page")

        image_data, content_type, filename = loader._download_image(
            "https://example.com/test.jpg", "test.jpg"
        )

        self.assertEqual(image_data, b"fake_image_data_that_is_long_enough")
        self.assertEqual(content_type, "image/jpeg")
        self.assertEqual(filename, "test.jpg")

    @patch("requests.get")
    def test_download_image_too_small(self, mock_requests):
        """Test that very small images are rejected."""
        # Mock small image response
        mock_response = MagicMock()
        mock_response.content = b"tiny"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        loader = BookLoaderURL("https://example.com/test-page")

        image_data, content_type, filename = loader._download_image(
            "https://example.com/test.jpg", "test.jpg"
        )

        # Should return None for all values due to small size
        self.assertIsNone(image_data)
        self.assertIsNone(content_type)
        self.assertIsNone(filename)

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        loader = BookLoaderURL("https://example.com/test-page")

        # Test normal filename
        self.assertEqual(loader._sanitize_filename("test.jpg"), "test.jpg")

        # Test filename with unsafe characters
        self.assertEqual(
            loader._sanitize_filename("test file!@#$%^&*().jpg"), "test_file__________.jpg"
        )

        # Test very long filename
        long_name = "a" * 200 + ".jpg"
        result = loader._sanitize_filename(long_name)
        self.assertTrue(len(result) <= 200)
        self.assertTrue(result.endswith(".jpg"))
