"""Integration tests for URL import anchor map creation and internal link handling."""

from unittest.mock import MagicMock, patch

import allure
import pytest
from django.contrib.auth import get_user_model

from django.test import Client

from lexiflux.ebook.book_loader_url import BookLoaderURL
from lexiflux.models import ReadingLoc


@allure.epic("Book import")
@allure.feature("URL import integration tests")
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

    def test_url_import_internal_links_functionality(self, db_init):
        """Test that URL import with minimal cleaning preserves internal links and creates accurate anchor map."""
        html_content = (
            """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Internal Links Navigation Test</title>
            <meta name="author" content="Link Author">
        </head>
        <body>
            <h1 id="introduction">Introduction</h1>
            <p>This is the introduction section with some content to make it substantial.</p>
            <p>Navigate to <a href="#section1">Section 1</a> or <a href="#section2">Section 2</a></p>
            <p>You can also jump to the <a href="#conclusion">Conclusion</a></p>
            """
            + ("Some filler content to ensure page breaks occur naturally. " * 40)
            + """

            <h2 id="section1">Section 1: First Topic</h2>
            <p>This is section 1 content with detailed information about the first topic.</p>
            <p>Go back to <a href="#introduction">Introduction</a> or continue to <a href="#section2">Section 2</a></p>
            """
            + ("More substantial content to create realistic page breaks. " * 40)
            + """

            <h2 id="section2">Section 2: Second Topic</h2>
            <p>This is section 2 with information about the second topic.</p>
            <p>Navigate back to <a href="#introduction">Introduction</a> or <a href="#section1">Section 1</a></p>
            <p>Or proceed to the <a href="#subsection">Subsection</a></p>
            """
            + ("Additional content for proper page separation and realistic content length. " * 35)
            + """

            <h3 id="subsection">Important Subsection</h3>
            <p>A subsection with more detailed information and analysis.</p>
            <p>Return to <a href="#section2">Section 2</a> or jump to <a href="#conclusion">Conclusion</a></p>
            """
            + ("Content to ensure the conclusion ends up on a different page. " * 30)
            + """

            <h2 id="conclusion">Conclusion</h2>
            <p>This is the conclusion section that summarizes everything.</p>
            <p>Return to <a href="#introduction">Introduction</a> to start over.</p>
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

            # Use minimal cleaning to preserve internal links (crucial for this test)
            loader = BookLoaderURL(
                "https://example.com/internal-links-test", cleaning_level="minimal"
            )
            book = loader.create("")
            book.owner = user
            book.public = True
            book.save()

            assert book.title == "Internal Links Navigation Test"
            assert book.author.name == "Link Author"
            assert book.pages.count() > 1  # Should span multiple pages

            assert isinstance(book.anchor_map, dict)
            assert len(book.anchor_map) > 0

            expected_anchors = [
                "#introduction",
                "#section1",
                "#section2",
                "#subsection",
                "#conclusion",
            ]

            for anchor in expected_anchors:
                assert anchor in book.anchor_map, (
                    f"Anchor {anchor} not found in anchor_map. Available: {list(book.anchor_map.keys())}"
                )

                anchor_info = book.anchor_map[anchor]
                assert "page" in anchor_info, f"Anchor {anchor} missing 'page' info"
                assert isinstance(anchor_info["page"], int), f"Anchor {anchor} page should be int"
                assert anchor_info["page"] > 0, f"Anchor {anchor} page should be positive"
                assert anchor_info["page"] <= book.pages.count(), (
                    f"Anchor {anchor} page exceeds book pages"
                )

                assert "item_id" in anchor_info, f"Anchor {anchor} missing 'item_id'"
                assert "item_name" in anchor_info, f"Anchor {anchor} missing 'item_name'"

            full_content = ""
            for page in book.pages.all():
                full_content += page.content

            for anchor in ["#section1", "#section2", "#conclusion"]:
                assert (
                    f'href="{anchor}"' in full_content or f'data-href="{anchor}"' in full_content
                ), f"Internal link to {anchor} not preserved in content"

            client = Client()
            client.force_login(user)

            section1_anchor = "#section1"
            response = client.post("/link_click", {"book-code": book.code, "link": section1_anchor})

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] == True, f"Link click failed: {response_data}"
            assert "page_number" in response_data
            assert "word" in response_data

            expected_page = book.anchor_map[section1_anchor]["page"]
            assert response_data["page_number"] == expected_page

            conclusion_anchor = "#conclusion"
            response = client.post(
                "/link_click", {"book-code": book.code, "link": conclusion_anchor}
            )

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] == True
            assert response_data["page_number"] == book.anchor_map[conclusion_anchor]["page"]

            assert response_data["word"] >= 0

            response = client.post(
                "/link_click", {"book-code": book.code, "link": "#nonexistent_anchor"}
            )

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] == False
            assert "error" in response_data
            assert "not found in anchor map" in response_data["error"]

            reading_loc = ReadingLoc.objects.get(user=user, book=book)
            assert reading_loc.page_number == book.anchor_map[conclusion_anchor]["page"]

            assert len(reading_loc.jump_history) > 0
            latest_jump = reading_loc.jump_history[-1]
            assert latest_jump["page_number"] == book.anchor_map[conclusion_anchor]["page"]

            page_numbers = {anchor: book.anchor_map[anchor]["page"] for anchor in expected_anchors}
            unique_pages = set(page_numbers.values())
            assert len(unique_pages) > 1, "All anchors shouldn't be on the same page for this test"

            intro_response = client.post(
                "/link_click", {"book-code": book.code, "link": "#introduction"}
            )
            assert intro_response.status_code == 200
            intro_data = intro_response.json()
            assert intro_data["success"] == True

            section2_response = client.post(
                "/link_click", {"book-code": book.code, "link": "#section2"}
            )
            assert section2_response.status_code == 200
            section2_data = section2_response.json()
            assert section2_data["success"] == True

            if intro_data["page_number"] != section2_data["page_number"]:
                assert abs(intro_data["page_number"] - section2_data["page_number"]) >= 1

    def test_url_import_navigation_content_accuracy(self, db_init):
        """Test that internal link navigation lands at the correct content location with accurate word positioning."""
        html_content = (
            """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Content Navigation Test</title>
            <meta name="author" content="Test Author">
        </head>
        <body>
            <nav>
                <a href="#chapter1">Go to Chapter 1</a>
                <a href="#chapter2">Go to Chapter 2</a>
                <a href="#important_note">See Important Note</a>
                <a href="#chapter3">Go to Chapter 3</a>
            </nav>

            <h1 id="chapter1">Chapter 1: The Beginning</h1>
            <p>This is the start of our story with introductory content.</p>
            <p>Continue reading <a href="#chapter2">Chapter 2</a>.</p>
            """
            + ("Content to create page separation. " * 50)
            + """

            <h2 id="chapter2">Chapter 2: The Middle Part</h2>
            <p>Here we dive into the middle section of the narrative.</p>
            <p>Check the <a href="#important_note">Important Note</a> before proceeding.</p>
            """
            + ("More content for realistic pagination. " * 50)
            + """

            <h3 id="important_note">Important Note About Something</h3>
            <p>This is a crucial point that readers need to understand.</p>
            <p>Now proceed to <a href="#chapter3">Chapter 3</a>.</p>
            """
            + ("Additional content to ensure proper page breaks. " * 40)
            + """

            <h2 id="chapter3">Chapter 3: The Final Section</h2>
            <p>We conclude our journey in this final chapter.</p>
            <p>Return to <a href="#chapter1">Chapter 1</a> if needed.</p>
        </body>
        </html>
        """
        )

        User = get_user_model()
        user = User.objects.create_user(username="contentuser", password="testpass")
        user.is_approved = True
        user.save()

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = html_content
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            loader = BookLoaderURL("https://example.com/content-nav-test", cleaning_level="minimal")
            book = loader.create("")
            book.owner = user
            book.save()

            assert isinstance(book.anchor_map, dict)
            assert len(book.anchor_map) > 0

            expected_anchors = ["#chapter1", "#chapter2", "#important_note", "#chapter3"]
            available_anchors = list(book.anchor_map.keys())

            for anchor in expected_anchors:
                assert anchor in book.anchor_map, (
                    f"Anchor {anchor} not found. Available: {available_anchors}"
                )

            # Debug: print anchor_map to understand the structure
            print(f"Anchor map: {book.anchor_map}")
            for anchor, info in book.anchor_map.items():
                if anchor in expected_anchors:
                    page = book.pages.get(number=info["page"])
                    print(f"Anchor {anchor}: page {info['page']}, has {len(page.words)} words")

            client = Client()
            client.force_login(user)

            response = client.post("/link_click", {"book-code": book.code, "link": "#chapter1"})

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] == True, f"Navigation failed: {response_data}"

            target_page = book.pages.get(number=response_data["page_number"])
            word_position = response_data["word"]

            # Debug: show more context around the landing position
            full_content = target_page.content
            print(f"Page content length: {len(full_content)}")
            print(f"Word position: {word_position} out of {len(target_page.words)} words")

            start_word = max(0, word_position - 5)
            end_word = min(len(target_page.words), word_position + 15)
            context_fragment, _ = target_page.extract_words(start_word, end_word)

            print(f"Context fragment: '{context_fragment}'")

            assert "Chapter 1" in context_fragment or "Beginning" in context_fragment, (
                f"Navigation to #chapter1 landed at wrong content. Got: '{context_fragment}'"
            )

            response = client.post(
                "/link_click", {"book-code": book.code, "link": "#important_note"}
            )

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] == True

            note_page = book.pages.get(number=response_data["page_number"])
            note_word_pos = response_data["word"]

            start_word = max(0, note_word_pos - 3)
            end_word = min(len(note_page.words), note_word_pos + 10)
            note_context, _ = note_page.extract_words(start_word, end_word)

            assert "Important Note" in note_context or "Something" in note_context, (
                f"Navigation to #important_note landed at wrong content. Got: '{note_context}'"
            )

            response = client.post("/link_click", {"book-code": book.code, "link": "#chapter3"})

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] == True

            chapter3_page = book.pages.get(number=response_data["page_number"])
            chapter3_word_pos = response_data["word"]

            start_word = max(0, chapter3_word_pos - 2)
            end_word = min(len(chapter3_page.words), chapter3_word_pos + 10)
            chapter3_context, _ = chapter3_page.extract_words(start_word, end_word)

            assert "Chapter 3" in chapter3_context or "Final Section" in chapter3_context, (
                f"Navigation to #chapter3 landed at wrong content. Got: '{chapter3_context}'"
            )

            response1 = client.post("/link_click", {"book-code": book.code, "link": "#chapter1"})
            response2 = client.post("/link_click", {"book-code": book.code, "link": "#chapter2"})

            page1 = book.pages.get(number=response1.json()["page_number"])
            page2 = book.pages.get(number=response2.json()["page_number"])

            word_pos1 = response1.json()["word"]
            word_pos2 = response2.json()["word"]

            context1, _ = page1.extract_words(
                max(0, word_pos1 - 2), min(len(page1.words), word_pos1 + 8)
            )
            context2, _ = page2.extract_words(
                max(0, word_pos2 - 2), min(len(page2.words), word_pos2 + 8)
            )

            assert context1 != context2, (
                "Different anchors should lead to different content contexts"
            )

            assert "Chapter 1" in context1 or "Beginning" in context1
            assert "Chapter 2" in context2 or "Middle Part" in context2

            first_nav = client.post("/link_click", {"book-code": book.code, "link": "#chapter2"})
            second_nav = client.post("/link_click", {"book-code": book.code, "link": "#chapter2"})

            assert first_nav.json()["page_number"] == second_nav.json()["page_number"]
            assert first_nav.json()["word"] == second_nav.json()["word"]
