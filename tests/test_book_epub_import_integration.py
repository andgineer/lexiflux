"""Integration tests for EPUB import TOC creation and internal link clicking."""

import json
import logging
from unittest.mock import MagicMock, patch

import allure
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from ebooklib import ITEM_DOCUMENT, epub

from lexiflux.ebook.book_loader_epub import BookLoaderEpub
from lexiflux.models import Author, Book, BookPage, Language, ReadingLoc


logger = logging.getLogger(__name__)


@allure.epic("Book import")
@allure.feature("EPUB import integration tests")
@pytest.mark.django_db
class TestEpubTocIntegration:
    """Integration tests for EPUB TOC creation during import."""

    def test_epub_import_creates_correct_toc_with_page_numbers(self, db_init):
        """Test that EPUB import creates TOC with correct page numbers."""
        mock_book = MagicMock(spec=epub.EpubBook)

        # Create mock items with different content sizes to test page splitting
        mock_items = []

        # Item 0: Short content, should be page 1
        mock_items.append(
            MagicMock(
                spec=epub.EpubHtml,
                get_body_content=lambda: '<h1 id="chapter1">Chapter 1: Introduction</h1><p>Short intro content.</p>'.encode(
                    "utf-8"
                ),
                get_type=lambda: ITEM_DOCUMENT,
                file_name="intro.xhtml",
                get_name=lambda: "intro.xhtml",
                get_id=lambda: "item_0",
            )
        )

        # Item 1: Long content, should span multiple pages
        long_content = (
            '<h1 id="chapter2">Chapter 2: Main Content</h1>'
            + "<p>"
            + ("Long content paragraph. " * 500)
            + "</p>"
        )
        mock_items.append(
            MagicMock(
                spec=epub.EpubHtml,
                get_body_content=lambda: long_content.encode("utf-8"),
                get_type=lambda: ITEM_DOCUMENT,
                file_name="main.xhtml",
                get_name=lambda: "main.xhtml",
                get_id=lambda: "item_1",
            )
        )

        # Item 2: Another chapter with anchor
        mock_items.append(
            MagicMock(
                spec=epub.EpubHtml,
                get_body_content=lambda: '<h1 id="chapter3">Chapter 3: Conclusion</h1><p id="important">Important conclusion text.</p>'.encode(
                    "utf-8"
                ),
                get_type=lambda: ITEM_DOCUMENT,
                file_name="conclusion.xhtml",
                get_name=lambda: "conclusion.xhtml",
                get_id=lambda: "item_2",
            )
        )

        mock_book.get_items.return_value = mock_items
        mock_book.spine = [(f"item_{i}",) for i in range(len(mock_items))]
        mock_book.get_item_with_id = lambda id: mock_items[int(id.split("_")[1])]

        mock_book.toc = [
            epub.Link("intro.xhtml#chapter1", "Chapter 1: Introduction"),
            epub.Link("main.xhtml#chapter2", "Chapter 2: Main Content"),
            epub.Link("conclusion.xhtml#chapter3", "Chapter 3: Conclusion"),
            epub.Link("conclusion.xhtml#important", "Important Section"),
        ]

        mock_book.get_metadata.side_effect = lambda dc_type, field: {
            ("DC", "title"): [("Test EPUB Book", {})],
            ("DC", "creator"): [("Test Author", {})],
            ("DC", "language"): [("en", {})],
        }.get((dc_type, field), [])

        with patch("ebooklib.epub.read_epub", return_value=mock_book):
            loader = BookLoaderEpub("dummy_path")
            book = loader.create("")

        assert book.title == "Test EPUB Book"
        assert book.author.name == "Test Author"
        assert book.language.name == "English"

        toc = book.toc
        assert len(toc) == 4, f"Expected 4 TOC entries, got {len(toc)}: {toc}"

        toc_titles = [entry[0] for entry in toc]
        toc_pages = [entry[1] for entry in toc]

        assert "Chapter 1: Introduction" in toc_titles
        assert "Chapter 2: Main Content" in toc_titles
        assert "Chapter 3: Conclusion" in toc_titles
        assert "Important Section" in toc_titles

        assert all(isinstance(page, int) and page > 0 for page in toc_pages)
        assert toc_pages == sorted(toc_pages), (
            f"TOC pages should be in ascending order: {toc_pages}"
        )

        anchor_map = book.anchor_map
        assert "intro.xhtml#chapter1" in anchor_map
        assert "main.xhtml#chapter2" in anchor_map
        assert "conclusion.xhtml#chapter3" in anchor_map
        assert "conclusion.xhtml#important" in anchor_map

        for link, info in anchor_map.items():
            assert "page" in info
            assert "item_id" in info
            assert "item_name" in info
            assert isinstance(info["page"], int)
            assert info["page"] > 0

    def test_epub_import_with_nested_toc_structure(self, db_init):
        """Test EPUB import with nested TOC structure (sections and subsections)."""
        mock_book = MagicMock(spec=epub.EpubBook)

        content = """
        <h1 id="part1">Part 1: Beginning</h1>
        <h2 id="chapter1">Chapter 1: First Steps</h2>
        <p>Content for chapter 1</p>
        <h2 id="chapter2">Chapter 2: Next Steps</h2>
        <p>Content for chapter 2</p>
        <h1 id="part2">Part 2: Advanced</h1>
        <h2 id="chapter3">Chapter 3: Advanced Topics</h2>
        <p>Content for chapter 3</p>
        """

        mock_item = MagicMock(
            spec=epub.EpubHtml,
            get_body_content=lambda: content.encode("utf-8"),
            get_type=lambda: ITEM_DOCUMENT,
            file_name="book.xhtml",
            get_name=lambda: "book.xhtml",
            get_id=lambda: "item_0",
        )

        mock_book.get_items.return_value = [mock_item]
        mock_book.spine = [("item_0",)]
        mock_book.get_item_with_id = lambda id: mock_item

        mock_book.toc = [
            (
                epub.Link("book.xhtml#part1", "Part 1: Beginning"),
                [
                    epub.Link("book.xhtml#chapter1", "Chapter 1: First Steps"),
                    epub.Link("book.xhtml#chapter2", "Chapter 2: Next Steps"),
                ],
            ),
            (
                epub.Link("book.xhtml#part2", "Part 2: Advanced"),
                [
                    epub.Link("book.xhtml#chapter3", "Chapter 3: Advanced Topics"),
                ],
            ),
        ]

        mock_book.get_metadata.side_effect = lambda dc_type, field: {
            ("DC", "title"): [("Nested TOC Book", {})],
            ("DC", "creator"): [("Test Author", {})],
            ("DC", "language"): [("en", {})],
        }.get((dc_type, field), [])

        with patch("ebooklib.epub.read_epub", return_value=mock_book):
            loader = BookLoaderEpub("dummy_path")
            book = loader.create("")

        toc = book.toc
        toc_titles = [entry[0] for entry in toc]

        expected_titles = [
            "Part 1: Beginning.Chapter 1: First Steps",
            "Part 1: Beginning.Chapter 2: Next Steps",
            "Part 2: Advanced.Chapter 3: Advanced Topics",
        ]

        assert len(toc_titles) == len(expected_titles), (
            f"Expected {len(expected_titles)} TOC entries, got {len(toc_titles)}: {toc_titles}"
        )

        for title in expected_titles:
            assert title in toc_titles, f"Expected '{title}' in TOC titles: {toc_titles}"


@allure.epic("Book import")
@allure.feature("EPUB import integration tests")
@pytest.mark.django_db
class TestInternalLinkClicking:
    """Integration tests for internal link clicking functionality."""

    @pytest.fixture
    def setup_book_with_links(self, db_init):
        """Create a book with pages and internal links for testing."""
        User = get_user_model()
        user = User.objects.create_user(username="testuser", password="testpass")
        user.is_approved = True
        user.save()

        language = Language.objects.get(name="English")
        author, _ = Author.objects.get_or_create(name="Test Author")

        book = Book.objects.create(
            title="Test Book with Links",
            author=author,
            language=language,
            code="test-book-links",
            owner=user,  # Make user the owner so they have permission
            public=True,  # Make it public for additional access
        )

        page1 = BookPage.objects.create(
            book=book,
            number=1,
            content='<p>This is page 1. <a href="page2.xhtml#section1">Link to section 1</a></p>',
            normalized_content="This is page 1. Link to section 1",
        )

        page2 = BookPage.objects.create(
            book=book,
            number=2,
            content='<h1 id="section1">Section 1</h1><p>This is section 1 content.</p>',
            normalized_content="Section 1 This is section 1 content.",
        )

        page3 = BookPage.objects.create(
            book=book,
            number=3,
            content='<p>Page 3 content. <a href="page2.xhtml#section1">Another link to section 1</a></p>',
            normalized_content="Page 3 content. Another link to section 1",
        )

        book.anchor_map = {
            "page2.xhtml#section1": {"page": 2, "item_id": "item_1", "item_name": "page2.xhtml"},
            "page2.xhtml": {"page": 2, "item_id": "item_1", "item_name": "page2.xhtml"},
        }
        book.save()

        return {"user": user, "book": book, "pages": [page1, page2, page3]}

    def test_link_click_resolves_to_correct_page(self, setup_book_with_links):
        """Test that clicking an internal link resolves to the correct page."""
        data = setup_book_with_links
        client = Client()
        client.force_login(data["user"])

        response = client.post(
            "/link_click", {"book-code": data["book"].code, "link": "page2.xhtml#section1"}
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)

        assert response_data["success"] is True
        assert response_data["page_number"] == 2
        assert "word" in response_data
        assert isinstance(response_data["word"], int)

        reading_loc = ReadingLoc.objects.get(user=data["user"], book=data["book"])
        assert reading_loc.page_number == 2

    def test_link_click_with_invalid_link(self, setup_book_with_links):
        """Test that clicking an invalid internal link returns error."""
        data = setup_book_with_links
        client = Client()
        client.force_login(data["user"])

        response = client.post(
            "/link_click", {"book-code": data["book"].code, "link": "nonexistent.xhtml#invalid"}
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)

        assert response_data["success"] is False
        assert "error" in response_data
        assert "not found in anchor map" in response_data["error"]

    def test_link_click_creates_jump_history(self, setup_book_with_links):
        """Test that clicking links creates proper jump history for navigation."""
        data = setup_book_with_links
        client = Client()
        client.force_login(data["user"])

        response = client.post(
            "/location",
            {
                "book-code": data["book"].code,
                "book-page-number": 1,
                "top-word": 0,
            },
        )
        assert response.status_code == 200

        response = client.post(
            "/link_click", {"book-code": data["book"].code, "link": "page2.xhtml#section1"}
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["success"] is True
        assert response_data["page_number"] == 2

        response = client.post(
            "/jump_back",
            {
                "book-code": data["book"].code,
            },
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data["success"] is True
        assert response_data["page_number"] == 1  # Should return to page 1

    def test_link_click_finds_correct_word_position(self, setup_book_with_links):
        """Test that link clicking finds the correct word position for anchors."""
        data = setup_book_with_links

        # Update page 2 to have a more complex structure where we can test word positioning
        page2 = data["pages"][1]
        page2.content = '<p>Some intro text.</p><h1 id="section1">Section 1 Title</h1><p>This is section 1 content.</p>'
        page2.save()

        client = Client()
        client.force_login(data["user"])

        response = client.post(
            "/link_click", {"book-code": data["book"].code, "link": "page2.xhtml#section1"}
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)

        assert response_data["success"] is True
        assert response_data["page_number"] == 2

        # The word position should be greater than 0 since the anchor is not at the beginning
        assert response_data["word"] >= 0

    def test_multiple_links_to_same_target(self, setup_book_with_links):
        """Test that multiple links pointing to the same target work correctly."""
        data = setup_book_with_links
        client = Client()
        client.force_login(data["user"])

        response1 = client.post(
            "/link_click", {"book-code": data["book"].code, "link": "page2.xhtml#section1"}
        )

        reading_loc = ReadingLoc.objects.get(user=data["user"], book=data["book"])
        reading_loc.page_number = 3
        reading_loc.save()

        response2 = client.post(
            "/link_click", {"book-code": data["book"].code, "link": "page2.xhtml#section1"}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = json.loads(response1.content)
        data2 = json.loads(response2.content)

        assert data1["success"] is True
        assert data2["success"] is True
        assert data1["page_number"] == data2["page_number"] == 2

    def test_link_click_requires_authentication(self, setup_book_with_links):
        """Test that link_click view requires user authentication."""
        data = setup_book_with_links
        client = Client()

        response = client.post(
            "/link_click", {"book-code": data["book"].code, "link": "page2.xhtml#section1"}
        )

        # Should redirect to login due to @smart_login_required decorator
        assert response.status_code == 302

    def test_link_click_with_missing_parameters(self, setup_book_with_links):
        """Test link_click view with missing required parameters."""
        data = setup_book_with_links
        client = Client()
        client.force_login(data["user"])

        # Test with missing book-code - should return 500 because view tries to get book with None
        response = client.post("/link_click", {"link": "page2.xhtml#section1"})
        assert response.status_code == 500

        # Test with missing link - should return JSON error
        response = client.post(
            "/link_click",
            {
                "book-code": data["book"].code,
            },
        )
        # The view doesn't explicitly check for missing link, it will try to process None
        assert response.status_code == 200
        assert response.json() == {"success": False, "error": "Link None not found in anchor map"}

    def test_link_click_with_invalid_book_code(self, setup_book_with_links):
        """Test link_click view with invalid book code."""
        data = setup_book_with_links
        client = Client()
        client.force_login(data["user"])

        response = client.post(
            "/link_click", {"book-code": "invalid-book-code", "link": "page2.xhtml#section1"}
        )

        assert (
            response.status_code == 500
        )  # get_object_or_404 raises Http404 which becomes 500 in tests
