"""Integration tests for URL import anchor map creation and internal link handling."""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from lexiflux.ebook.book_loader_url import BookLoaderURL


@pytest.mark.django_db
class TestUrlImportIntegration:
    """Integration tests for URL import anchor map creation and internal link handling."""

    def test_url_import_creates_book_with_minimal_cleaning(self, db_init):
        """Test that URL import with minimal cleaning preserves internal links."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Article with Links</title>
            <meta name="author" content="Test Author">
        </head>
        <body>
            <h1 id="introduction">Introduction</h1>
            <p>This is the introduction. <a href="#section1">Go to Section 1</a></p>
            
            <h2 id="section1">Section 1: Overview</h2>
            <p>This is section 1. <a href="#section2">Continue to Section 2</a></p>
            
            <h2 id="section2">Section 2: Details</h2>
            <p>This is section 2. <a href="#introduction">Back to Introduction</a></p>
            
            <p>External link: <a href="https://external.com">External Site</a></p>
        </body>
        </html>
        """

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            loader = BookLoaderURL("https://example.com/test-article", cleaning_level="minimal")
            book = loader.create("")

            assert book.title == "Test Article with Links"
            assert book.author.name == "Test Author"
            assert book.language.name == "English"

            # With minimal cleaning, we should preserve some structure
            # Get page content to verify content was imported
            page_content = ""
            for page in book.pages.all():
                page_content += page.content

            assert "Introduction" in page_content
            assert "Section 1: Overview" in page_content
            assert "Section 2: Details" in page_content

            assert hasattr(book, "anchor_map")
            assert isinstance(book.anchor_map, dict)

    def test_url_import_basic_functionality(self, db_init):
        """Test basic URL import functionality and content extraction."""
        html_content = (
            """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Navigation Test Article</title>
            <meta name="author" content="Web Author">
        </head>
        <body>
            <article>
                <h1>Navigation Test Article</h1>
                <p>Page 1 content with important information.</p>
                """
            + ("Some filler content to make it substantial. " * 100)
            + """
                
                <h2>Chapter 2: Main Content</h2>
                <p>This is chapter 2 content with more details.</p>
            </article>
        </body>
        </html>
        """
        )

        User = get_user_model()
        user = User.objects.create_user(username="testuser", password="testpass")
        user.is_approved = True
        user.save()

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            loader = BookLoaderURL("https://example.com/nav-test")
            book = loader.create("")
            book.owner = user
            book.public = True
            book.save()

            assert book.title == "Navigation Test Article"
            assert book.author.name == "Web Author"
            assert book.pages.count() > 0

            page_content = ""
            for page in book.pages.all():
                page_content += page.content

            assert "Navigation Test Article" in page_content
            assert "important information" in page_content or "filler content" in page_content

            assert "Source:" in page_content
            assert "https://example.com/nav-test" in page_content
            assert "Imported on:" in page_content

    def test_url_import_content_extraction_quality(self, db_init):
        """Test URL import content extraction with different cleaning levels."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Content Quality Test</title>
        </head>
        <body>
            <nav class="sidebar">
                <a href="#main">Navigation</a>
            </nav>
            <article>
                <header>
                    <h1>Content Quality Test</h1>
                    <p class="subtitle">Testing content extraction quality</p>
                </header>
                <main>
                    <p>This is the main content that should be preserved.</p>
                    <h2>Important Section</h2>
                    <p>This section contains important information that readers need.</p>
                </main>
            </article>
            <aside class="ads">
                <p>Advertisement content that should be removed</p>
            </aside>
            <footer>
                <p>Footer content</p>
            </footer>
        </body>
        </html>
        """

        cleaning_levels = ["minimal", "moderate", "aggressive"]

        for cleaning_level in cleaning_levels:
            with patch("requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.text = html_content
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value = mock_response

                loader = BookLoaderURL(
                    "https://example.com/content-test", cleaning_level=cleaning_level
                )
                book = loader.create("")

                assert book.title == "Content Quality Test"
                assert book.pages.count() > 0

                page_content = ""
                for page in book.pages.all():
                    page_content += page.content

                assert "main content that should be preserved" in page_content
                assert "Important Section" in page_content

                assert "Content Quality Test" in page_content  # Title
                assert "https://example.com/content-test" in page_content  # URL

    def test_url_import_metadata_extraction(self, db_init):
        """Test that URL import correctly extracts metadata from web pages."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Metadata Test Article</title>
            <meta name="author" content="John Doe">
            <meta name="description" content="A test article for metadata extraction">
            <meta property="og:title" content="Open Graph Title">
            <meta property="article:author" content="Jane Smith">
        </head>
        <body>
            <article>
                <h1>Metadata Test Article</h1>
                <p>This article tests metadata extraction capabilities.</p>
                <p>It should correctly identify the title and author from meta tags.</p>
            </article>
        </body>
        </html>
        """

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            loader = BookLoaderURL("https://example.com/metadata-test")
            book = loader.create("")

            assert book.title == "Open Graph Title"
            assert book.author.name in ["John Doe", "Jane Smith", "Unknown Author"]

            page_content = ""
            for page in book.pages.all():
                page_content += page.content

            assert "metadata extraction capabilities" in page_content
            assert "identify the title and author" in page_content

    def test_url_import_error_handling(self, db_init):
        """Test URL import error handling and fallback behavior."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error Handling Test</title>
        </head>
        <body>
            <h1>Error Handling Test</h1>
            <p>This tests error handling in URL import.</p>
        </body>
        </html>
        """

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            loader = BookLoaderURL("https://example.com/error-test")
            book = loader.create("")

            assert book.title == "Error Handling Test"
            assert book.pages.count() > 0

        # Test with request error (this should raise an exception)
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            with pytest.raises(Exception):
                loader = BookLoaderURL("https://example.com/error-test")

    def test_url_import_filename_generation(self, db_init):
        """Test that URL import generates appropriate filenames from URLs."""
        test_cases = [
            ("https://example.com", "example.com"),
            ("https://example.com/article", "example.com_article"),
            ("https://blog.example.com/post/123", "blog.example.com_123"),
            ("https://example.com/document.pdf", "document.pdf"),
        ]

        for url, expected_filename in test_cases:
            with patch("requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.text = (
                    "<html><head><title>Test</title></head><body><p>Content</p></body></html>"
                )
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value = mock_response

                loader = BookLoaderURL(url)
                filename = loader._get_filename_from_url()

                assert filename == expected_filename, (
                    f"URL {url} should generate filename {expected_filename}, got {filename}"
                )

    def test_url_import_source_info_integration(self, db_init):
        """Test that URL import adds source information that doesn't interfere with navigation."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Source Info Test</title>
        </head>
        <body>
            <h1 id="main-content">Main Content</h1>
            <p>Original content. <a href="#footer-section">Go to footer</a></p>
            
            <div id="footer-section">
                <p>Footer information.</p>
            </div>
        </body>
        </html>
        """

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            loader = BookLoaderURL("https://example.com/source-info-test")
            book = loader.create("")

            first_page = book.pages.first()
            assert first_page is not None

            page_content = first_page.content

            assert "Source Info Test" in page_content  # Title should be in content
            assert (
                "https://example.com/source-info-test" in page_content
            )  # URL should be in content
            assert "Imported on:" in page_content  # Date should be in content

            assert "Main Content" in page_content
            assert "Original content" in page_content

            assert hasattr(book, "anchor_map")
            assert isinstance(book.anchor_map, dict)

            if len(book.anchor_map) > 0:
                for link, info in book.anchor_map.items():
                    assert "page" in info
                    assert isinstance(info["page"], int)
                    assert info["page"] > 0
