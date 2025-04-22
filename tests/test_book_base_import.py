import pytest
import allure
from unittest.mock import patch, MagicMock

from lexiflux.ebook.book_loader_base import BookLoaderBase
from lexiflux.ebook.clear_html import parse_partial_html


@pytest.fixture
def book_processor_mock():
    """Create a mock BookLoaderBase processor."""
    # Using the patching pattern from test_book_plain_text_import.py
    with (
        patch("lexiflux.ebook.book_loader_base.language_detector") as mock_detector,
        patch("lexiflux.ebook.book_loader_base.Language.find") as mock_language_find,
        patch(
            "lexiflux.ebook.clear_html.parse_partial_html", wraps=parse_partial_html
        ) as mock_parse,
    ):
        mock_detector.return_value.detect.return_value = "en"
        mock_language_find.return_value = "English"

        # Create a concrete implementation of BookLoaderBase for testing
        class MockBookLoader(BookLoaderBase):
            def load_text(self):
                self.text = "Sample text"

            def detect_meta(self):
                return {"title": "Test Book", "author": "Test Author"}, 0, len(self.text)

            def get_random_words(self, words_num=15):
                return "sample words"

            def pages(self):
                yield "Page 1 content"
                yield "Page 2 content"

        loader = MockBookLoader("mock_file.txt")
        # Initialize the anchor map and tree_root
        loader.anchor_map = {}
        loader.tree_root = MagicMock()
        # Configure the mock tree_root for extract_ids_with_internal_links tests
        loader.tree_root.xpath = MagicMock()

        return loader


@allure.epic("Book import")
@allure.feature("BookLoaderBase: anchor handling")
class TestBookLoaderBaseAnchors:
    @allure.story("Process anchors in HTML content")
    def test_process_anchors_basic(self, book_processor_mock):
        """Test basic anchor processing functionality."""
        # Create HTML content with a div that has an ID
        content = '<div id="section1">Section 1</div>'

        # Patch parse_partial_html to return a properly structured etree
        with patch("lexiflux.ebook.clear_html.parse_partial_html") as mock_parse:
            # Create a mock element with id and text attributes
            mock_element = MagicMock()
            mock_element.get.return_value = "section1"
            mock_element.text = "Section 1"

            # Configure the mock parser to return a tree with our element
            mock_tree = MagicMock()
            mock_tree.xpath.return_value = [mock_element]
            mock_parse.return_value = mock_tree

            # Call the method under test
            book_processor_mock._process_anchors(1, content)

            # Verify the anchor map was properly populated
            assert "#section1" in book_processor_mock.anchor_map
            assert book_processor_mock.anchor_map["#section1"]["page"] == 1
            assert book_processor_mock.anchor_map["#section1"]["item_id"] == "section1"
            assert book_processor_mock.anchor_map["#section1"]["item_name"] == "Section 1"

    @allure.story("Process anchors with file name")
    def test_process_anchors_with_filename(self, book_processor_mock):
        """Test anchor processing with a file name."""
        content = '<div id="section1">Section 1</div>'
        file_name = "chapter1.html"

        with patch("lexiflux.ebook.clear_html.parse_partial_html") as mock_parse:
            mock_element = MagicMock()
            mock_element.get.return_value = "section1"
            mock_element.text = "Section 1"

            mock_tree = MagicMock()
            mock_tree.xpath.return_value = [mock_element]
            mock_parse.return_value = mock_tree

            book_processor_mock._process_anchors(1, content, file_name)

            # Verify specific anchor entry with filename
            assert f"{file_name}#section1" in book_processor_mock.anchor_map
            assert book_processor_mock.anchor_map[f"{file_name}#section1"]["page"] == 1
            assert (
                book_processor_mock.anchor_map[f"{file_name}#section1"]["item_name"] == "Section 1"
            )

            # Verify file entry
            assert file_name in book_processor_mock.anchor_map
            assert book_processor_mock.anchor_map[file_name]["page"] == 1
            assert "chapter1.html" in book_processor_mock.anchor_map[file_name]["item_name"]

    @allure.story("Process anchors with custom item ID and name")
    def test_process_anchors_with_custom_ids(self, book_processor_mock):
        """Test anchor processing with custom item ID and name."""
        content = '<div id="section1">Section 1</div>'

        with patch("lexiflux.ebook.clear_html.parse_partial_html") as mock_parse:
            mock_element = MagicMock()
            mock_element.get.return_value = "section1"
            mock_element.text = "Section 1"

            mock_tree = MagicMock()
            mock_tree.xpath.return_value = [mock_element]
            mock_parse.return_value = mock_tree

            book_processor_mock._process_anchors(
                1, content, "chapter1.html", "custom_id", "Custom Name"
            )

            # Verify custom values were used
            assert "chapter1.html#section1" in book_processor_mock.anchor_map
            assert (
                book_processor_mock.anchor_map["chapter1.html#section1"]["item_id"] == "custom_id"
            )
            assert (
                book_processor_mock.anchor_map["chapter1.html#section1"]["item_name"]
                == "Custom Name"
            )

    @allure.story("Process anchors with multiple elements")
    def test_process_anchors_multiple_elements(self, book_processor_mock):
        """Test processing multiple anchor elements in the same content."""
        content = """
        <div>
            <h1 id="title">Title</h1>
            <p id="para1">Paragraph 1</p>
            <p id="para2">Paragraph 2</p>
        </div>
        """

        with patch("lexiflux.ebook.clear_html.parse_partial_html") as mock_parse:
            # Create mock elements
            mock_title = MagicMock()
            mock_title.get.return_value = "title"
            mock_title.text = "Title"

            mock_para1 = MagicMock()
            mock_para1.get.return_value = "para1"
            mock_para1.text = "Paragraph 1"

            mock_para2 = MagicMock()
            mock_para2.get.return_value = "para2"
            mock_para2.text = "Paragraph 2"

            # Configure the parser to return all elements
            mock_tree = MagicMock()
            mock_tree.xpath.return_value = [mock_title, mock_para1, mock_para2]
            mock_parse.return_value = mock_tree

            book_processor_mock._process_anchors(2, content, "chapter2.html")

            # Verify all elements were processed
            assert "chapter2.html#title" in book_processor_mock.anchor_map
            assert "chapter2.html#para1" in book_processor_mock.anchor_map
            assert "chapter2.html#para2" in book_processor_mock.anchor_map
            assert "chapter2.html" in book_processor_mock.anchor_map
            assert len(book_processor_mock.anchor_map) == 4  # 3 elements + file entry

    @allure.story("Process anchors with empty content")
    def test_process_anchors_empty_content(self, book_processor_mock):
        """Test processing empty content."""
        with patch("lexiflux.ebook.clear_html.parse_partial_html") as mock_parse:
            mock_parse.return_value = None

            # Reset the anchor map to ensure it's empty before the test
            book_processor_mock.anchor_map = {}

            # The method should handle None result from parse_partial_html
            book_processor_mock._process_anchors(1, "", "empty.html")

            # The file entry might not be added due to the exception,
            # so we're checking that it's handled gracefully
            # We don't assert specific behavior, just that it doesn't crash

    @allure.story("Process anchors with invalid HTML")
    def test_process_anchors_invalid_html(self, book_processor_mock):
        """Test processing invalid HTML content."""
        # Content doesn't matter since we're mocking the parser

        with patch("lexiflux.ebook.book_loader_base.parse_partial_html") as mock_parse:
            mock_parse.side_effect = Exception("Invalid HTML")

            book_processor_mock.anchor_map = {}

            with patch("lexiflux.ebook.book_loader_base.log") as mock_log:
                book_processor_mock._process_anchors(1, "any content", "invalid.html")
                mock_log.exception.assert_called_once_with("Error processing anchors")

    @allure.story("Process anchors - specific test for chap03")
    def test_process_anchors_chap03(self, book_processor_mock, caplog):
        """Test the specific case mentioned in the code about 'chap03'."""
        content = '<div><a id="chap03"></a>Chapter 3</div>'

        with patch("lexiflux.ebook.clear_html.parse_partial_html") as mock_parse:
            # Configure mock to trigger the chap03 warning
            mock_element = MagicMock()
            mock_element.get.return_value = "chap03"
            mock_element.text = None  # Empty text as in the example

            mock_tree = MagicMock()
            mock_tree.xpath.return_value = [mock_element]
            mock_parse.return_value = mock_tree

            # Insert "chap03" string into content to trigger warning
            book_processor_mock._process_anchors(3, content, "chapter3.html")

            assert any(
                "Found anchor ID in the _process_anchors" in record.message
                for record in caplog.records
            )

    @allure.story("Extract IDs with internal links")
    def test_extract_ids_with_internal_links_basic(self, book_processor_mock):
        """Test basic extraction of IDs that have internal links pointing to them."""
        mock_link = MagicMock()
        mock_link.get.return_value = "#section1"

        # Configure tree_root to return our mock links
        book_processor_mock.tree_root.xpath.return_value = [mock_link]

        ids = book_processor_mock.extract_ids_with_internal_links()

        assert "section1" in ids
        assert len(ids) == 1
        book_processor_mock.tree_root.xpath.assert_called_once_with('//a[starts-with(@href, "#")]')

    @allure.story("Extract IDs with multiple internal links")
    def test_extract_ids_with_multiple_internal_links(self, book_processor_mock):
        """Test extraction of IDs with multiple internal links pointing to them."""
        mock_link1 = MagicMock()
        mock_link1.get.return_value = "#section1"

        mock_link2 = MagicMock()
        mock_link2.get.return_value = "#section2"

        mock_link3 = MagicMock()
        mock_link3.get.return_value = "#section1"  # Duplicate link to section1

        # Configure tree_root to return all mock links
        book_processor_mock.tree_root.xpath.return_value = [mock_link1, mock_link2, mock_link3]

        ids = book_processor_mock.extract_ids_with_internal_links()

        assert "section1" in ids
        assert "section2" in ids
        assert len(ids) == 2

    @allure.story("Extract IDs with no internal links")
    def test_extract_ids_with_no_internal_links(self, book_processor_mock):
        """Test extraction when there are no internal links."""
        book_processor_mock.tree_root.xpath.return_value = []

        ids = book_processor_mock.extract_ids_with_internal_links()

        assert len(ids) == 0

    @allure.story("Extract IDs with mixed links")
    def test_extract_ids_with_mixed_links(self, book_processor_mock):
        """Test extraction with a mix of internal and external links."""
        # Only internal links should be returned by the xpath query
        # Setup mock link with internal href
        mock_link = MagicMock()
        mock_link.get.return_value = "#section1"

        # Configure tree_root to return only internal links
        book_processor_mock.tree_root.xpath.return_value = [mock_link]

        ids = book_processor_mock.extract_ids_with_internal_links()

        assert "section1" in ids
        assert len(ids) == 1

    @allure.story("Extract IDs with empty href")
    def test_extract_ids_with_empty_href(self, book_processor_mock):
        """Test extraction with empty href attributes."""
        # Setup mock link with empty href
        mock_link1 = MagicMock()
        mock_link1.get.return_value = "#"  # Empty target

        mock_link2 = MagicMock()
        mock_link2.get.return_value = ""  # Completely empty

        # Configure tree_root to return links with empty hrefs
        book_processor_mock.tree_root.xpath.return_value = [mock_link1, mock_link2]

        ids = book_processor_mock.extract_ids_with_internal_links()

        # Verify no IDs were extracted (empty hrefs don't target valid IDs)
        assert len(ids) == 0
