import allure
import pytest
from unittest.mock import patch, MagicMock, ANY

from django.http import HttpRequest
from lxml import etree

from pagesmith import etree_to_str, parse_partial_html
from lexiflux.models import Author, Book, Language
from django.core.management import CommandError
from lexiflux.ebook.book_loader_url import BookLoaderURL, CleaningLevel
from lexiflux.ebook.book_loader_base import MetadataField

from bs4 import BeautifulSoup

from lexiflux.views.import_views import import_book


@pytest.fixture
def book_processor_url_mock():
    """Fixture to create a BookLoaderURL instance with mocked methods."""
    with (
        patch("requests.get"),
        patch("lexiflux.models.Language.find", return_value="English"),
        patch("lexiflux.models.Language.objects.filter"),
        patch("lexiflux.models.Language.objects.get_or_create"),
        patch.object(BookLoaderURL, "load_text"),
        patch.object(BookLoaderURL, "detect_meta") as mock_detect_meta,
        patch.object(BookLoaderURL, "detect_language", return_value="English"),
        patch.object(BookLoaderURL, "pages") as mock_pages,
        patch.object(BookLoaderURL, "_get_filename_from_url", return_value="test-page"),
    ):
        # Setup the mock pages to return two sample pages
        mock_pages.return_value = iter(["Page 1 content", "Page 2 content"])

        # Setup the mock detect_meta to return basic metadata
        mock_detect_meta.return_value = (
            {
                MetadataField.TITLE: "Test Book",
                MetadataField.AUTHOR: "Test Author",
                MetadataField.LANGUAGE: "English",
                MetadataField.RELEASED: None,
                MetadataField.CREDITS: None,
            },
            0,  # book_start
            100,  # book_end
        )

        loader = BookLoaderURL("https://example.com/test-page")
        loader.text = "<html><body><p>Test content</p></body></html>"
        loader.html_content = "<html><body><p>Test content</p></body></html>"
        loader.url = "https://example.com/test-page"
        yield loader


@allure.epic("Book import")
@allure.feature("URL import: success import")
@patch("lexiflux.models.Author.objects.get_or_create")
@patch("lexiflux.models.Language.objects.get_or_create")
@patch("lexiflux.models.Book.objects.create")
@patch("lexiflux.models.BookPage.objects.bulk_create")
@patch("lexiflux.models.BookPage.__init__", return_value=None)
def test_import_book_url_success(
    mock_book_page_init,
    mock_book_page_bulk_create,
    mock_book_create,
    mock_language_get_or_create,
    mock_author_get_or_create,
    book_processor_url_mock,
):
    mock_author_get_or_create.return_value = (MagicMock(spec=Author), True)
    mock_language_get_or_create.return_value = (MagicMock(spec=Language), True)

    mock_book = MagicMock(spec=Book)
    mock_book.title = "Test Book"
    mock_book_create.return_value = mock_book
    book_processor_url_mock.pages = MagicMock(return_value=["Page 1 content", "Page 2 content"])

    book = book_processor_url_mock.create("")

    assert book.title == "Test Book"

    # Verify that all mocks were called as expected
    mock_author_get_or_create.assert_called_once_with(name="Test Author")
    mock_language_get_or_create.assert_called_once_with(name="English")
    mock_book_create.assert_called_once_with(title="Test Book", author=ANY, language=ANY)

    # Check that BookPage.__init__ was called with the expected arguments
    # Instead of checking complex objects, check the arguments separately
    assert mock_book_page_init.call_count == 2

    calls = mock_book_page_init.call_args_list
    assert len(calls) == 2

    # Extract and check the keyword arguments from each call
    call1_kwargs = calls[0][1]
    call2_kwargs = calls[1][1]

    assert call1_kwargs["book"] == mock_book
    assert call1_kwargs["number"] == 1
    assert call1_kwargs["content"] == "Page 1 content"

    assert call2_kwargs["book"] == mock_book
    assert call2_kwargs["number"] == 2
    assert call2_kwargs["content"] == "Page 2 content"

    # Verify bulk_create was called once
    assert mock_book_page_bulk_create.call_count == 1


@allure.epic("Book import")
@allure.feature("URL import: public book")
@patch("lexiflux.models.CustomUser.objects.filter")
@patch("lexiflux.models.Book.objects.create")
@patch("lexiflux.models.BookPage.objects.bulk_create")
@patch("lexiflux.models.BookPage.__init__", return_value=None)
@patch("lexiflux.models.Author.objects.get_or_create")
@patch("lexiflux.models.Language.objects.get_or_create")
def test_import_book_url_without_owner_is_public(
    mock_language_get_or_create,
    mock_author_get_or_create,
    mock_book_page_init,
    mock_book_page_create,
    mock_book_create,
    mock_user_filter,
    book_processor_url_mock,
):
    mock_book = MagicMock(spec=Book)
    mock_book_create.return_value = mock_book
    mock_author_get_or_create.return_value = (MagicMock(), True)
    mock_language_get_or_create.return_value = (MagicMock(), True)

    book = book_processor_url_mock.create("")
    assert book.public is True


@allure.epic("Book import")
@allure.feature("URL import: failed import")
@patch("lexiflux.ebook.book_loader_base.CustomUser.objects.filter")
@patch("lexiflux.ebook.book_loader_base.Book.objects.create")
@patch("lexiflux.ebook.book_loader_base.BookPage.objects.create")
@patch("lexiflux.ebook.book_loader_base.Author.objects.get_or_create")
@patch("lexiflux.ebook.book_loader_base.Language.objects.get_or_create")
def test_import_book_nonexistent_owner_email(
    mock_language_get_or_create,
    mock_author_get_or_create,
    mock_book_page_create,
    mock_book_create,
    mock_user_filter,
    book_processor_url_mock,
):
    mock_user_filter.return_value.first.return_value = None
    mock_author_get_or_create.return_value = (MagicMock(), True)
    mock_language_get_or_create.return_value = (MagicMock(), True)
    mock_book = MagicMock()
    mock_book_create.return_value = mock_book

    with pytest.raises(CommandError) as exc_info:
        book_processor_url_mock.create("nonexistent@example.com")

    assert "no such user" in str(exc_info.value)


@allure.epic("Book import")
@allure.feature("URL import: success import")
@pytest.mark.django_db
def test_import_url_e2e():
    with (
        patch("requests.get") as mock_get,
        patch.object(
            BookLoaderURL, "__init__", return_value=None
        ),  # Patch __init__ to avoid real initialization
        patch("lexiflux.ebook.book_loader_url.parse_partial_html"),
        patch("lexiflux.ebook.book_loader_url.refine_html", return_value="<p>Cleaned content</p>"),
        patch("lexiflux.ebook.web_page_metadata.extract_web_page_metadata") as mock_metadata,
        patch.object(BookLoaderURL, "detect_meta"),
        patch.object(BookLoaderURL, "load_text"),  # Skip load_text to avoid serialization issues
        patch.object(BookLoaderURL, "pages"),
    ):
        mock_response = MagicMock()
        mock_response.text = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Alice's Adventures in Wonderland</title>
            <meta name="author" content="Lewis Carroll">
            <meta name="dc.language" content="English">
        </head>
        <body>
            <h1>Alice's Adventures in Wonderland</h1>
            <p>Chapter 1: Down the Rabbit-Hole</p>
            <p>Alice was beginning to get very tired of sitting by her sister on the bank...</p>
        </body>
        </html>
        """
        mock_get.return_value = mock_response

        # Setup metadata
        metadata = {
            MetadataField.TITLE: "Alice's Adventures in Wonderland",
            MetadataField.AUTHOR: "Lewis Carroll",
            MetadataField.LANGUAGE: "English",
            MetadataField.RELEASED: None,
            MetadataField.CREDITS: None,
        }
        mock_metadata.return_value = metadata

        # Create a loader object but bypass initialization
        book_loader = BookLoaderURL()

        # Set up required attributes manually
        book_loader.url = "https://example.com/alice.html"
        book_loader.text = "<p>Cleaned content</p>"
        book_loader.html_content = mock_response.text
        book_loader.meta = metadata
        book_loader.book_start = 0
        book_loader.book_end = 100
        book_loader.anchor_map = {}

        # Configure mock methods
        book_loader.detect_meta.return_value = (metadata, 0, 100)
        book_loader.pages.return_value = iter(["<p>Page content</p>"])

        # Create the book
        book = book_loader.create("")

        assert book.title == "Alice's Adventures in Wonderland"
        assert book.author.name == "Lewis Carroll"
        assert book.language.name == "English"
        assert book.public is True


@allure.epic("Book import")
@allure.feature("URL import: _get_filename_from_url")
def test_get_filename_from_url_various_urls():
    """Test extracting filenames from different URL patterns."""
    test_cases = [
        # Simple domain
        ("https://example.com", "example.com"),
        # Domain with trailing slash
        ("https://example.com/", "example.com"),
        # Domain with path
        ("https://example.com/article", "example.com_article"),
        # Domain with nested path
        ("https://example.com/blog/2023/05/article", "example.com_article"),
        # Domain with file extension
        ("https://example.com/download/document.pdf", "document.pdf"),
        # Domain with query parameters (should ignore them)
        ("https://example.com/search?q=test", "example.com_search"),
        # Domain with fragment (should ignore it)
        ("https://example.com/page#section", "example.com_page"),
        # URL with both query and fragment
        ("https://example.com/results?page=2#top", "example.com_results"),
        # Subdomain
        ("https://blog.example.com/post", "blog.example.com_post"),
        # Non-standard TLD
        ("https://example.co.uk/page", "example.co.uk_page"),
        # URL with numeric components
        ("https://example.com/article/12345", "example.com_12345"),
    ]

    # Create a mock instance that doesn't call the full initialization
    with patch.object(BookLoaderURL, "__init__", return_value=None):
        loader = BookLoaderURL()
        for url, expected_filename in test_cases:
            loader.url = url
            assert loader._get_filename_from_url() == expected_filename, f"Failed for URL: {url}"


@allure.epic("Book import")
@allure.feature("URL import: _add_source_info")
def test_add_source_info_title_and_source():
    """Test that _add_source_info adds title and source URL."""
    # Create a mock instance that doesn't call the full initialization
    with patch.object(BookLoaderURL, "__init__", return_value=None):
        loader = BookLoaderURL()
        loader.url = "https://example.com/test-article"
        loader.meta = {
            MetadataField.TITLE: "Test Article Title",
            MetadataField.AUTHOR: "Test Author",
            MetadataField.LANGUAGE: "English",
        }
        html_content = "<p>This is some test content.</p>"
        loader.text = html_content
        loader.book_start, loader.book_end = 0, len(loader.text)

        loader.tree_root = parse_partial_html(html_content)
        loader._add_source_info()
        result = etree_to_str(loader.tree_root)

        # Parse the result for easier testing
        soup = BeautifulSoup(result, "html.parser")

        # Check if source-info div exists
        source_div = soup.find("div", class_="source-info")
        assert source_div is not None, "Source info div not found"

        # Check title
        title = source_div.find("h1")
        assert title is not None, "Title heading not found"
        assert title.text == "Test Article Title", "Title text doesn't match"

        # Check source URL
        source_p = source_div.find_all("p")[0]
        assert source_p is not None, "Source paragraph not found"
        assert "Source: " in source_p.text, "Source label not found in text"

        # Check for clickable link
        source_link = source_p.find("a")
        assert source_link is not None, "Source link not found"
        assert source_link.get("href") == "https://example.com/test-article", (
            "Link href doesn't match URL"
        )
        assert source_link.get("target") == "_blank", "Link should open in new tab"
        assert source_link.text == "https://example.com/test-article", "Link text doesn't match URL"


@allure.epic("Book import")
@allure.feature("URL import: _add_source_info")
def test_add_source_info_date_and_formatting():
    """Test that _add_source_info adds current date and proper formatting."""
    # Create a mock instance that doesn't call the full initialization
    with patch.object(BookLoaderURL, "__init__", return_value=None):
        loader = BookLoaderURL()
        loader.url = "https://example.com/test-article"
        loader.meta = {
            MetadataField.TITLE: "Test Article Title",
            MetadataField.AUTHOR: "Test Author",
            MetadataField.LANGUAGE: "English",
        }

        html_content = "<p>This is some test content.</p>"
        loader.text = html_content
        loader.book_start, loader.book_end = 0, len(loader.text)

        # Use a specific date for testing consistency
        formatted_date = "2023-05-10 15:30:45"

        # Create a mock datetime object with a configured strftime method
        mock_date = MagicMock()
        mock_date.strftime.return_value = formatted_date

        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_date
            loader.tree_root = parse_partial_html(html_content)
            loader._add_source_info()
            result = etree_to_str(loader.tree_root)

        # Parse the result for easier testing
        soup = BeautifulSoup(result, "html.parser")

        # Check date
        date_p = soup.find_all("p")[1]
        assert date_p is not None, "Date paragraph not found"
        assert f"Imported on: {formatted_date}" in date_p.text, "Formatted date not found"


@allure.epic("Book import")
@allure.feature("URL import: _add_source_info")
def test_add_source_info_body_placement():
    """Test that _add_source_info correctly places content at the beginning of body."""
    # Create a mock instance that doesn't call the full initialization
    with patch.object(BookLoaderURL, "__init__", return_value=None):
        loader = BookLoaderURL()
        loader.url = "https://example.com/test-article"
        loader.meta = {
            MetadataField.TITLE: "Test Article Title",
            MetadataField.AUTHOR: "Test Author",
            MetadataField.LANGUAGE: "English",
        }

        # Test with a full HTML document
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
        </head>
        <body>
            <h1>Original Heading</h1>
            <p>Original paragraph.</p>
        </body>
        </html>
        """
        loader.text = html_content
        loader.book_start, loader.book_end = 0, len(loader.text)
        loader.tree_root = parse_partial_html(html_content)
        result = etree_to_str(loader.tree_root)
        print(result)
        loader._add_source_info()
        result = etree_to_str(loader.tree_root)
        print(result)

        # Parse the result
        soup = BeautifulSoup(result, "html.parser")

        # Check that source div is the first element in body
        body = soup.find("body")
        assert body is not None, "Body tag not found"

        # Get the first actual element (skipping any whitespace text nodes)
        first_element = None
        for child in body.children:
            if child.name is not None:  # Skip NavigableString objects
                first_element = child
                break

        assert first_element is not None, "No elements found in body"
        assert first_element.name == "div", "First element is not a div"
        assert first_element.get("class") == ["source-info"], (
            "First element does not have source-info class"
        )

        original_heading = soup.find("h1", string="Original Heading")
        assert original_heading is not None, "Original heading not found"
        assert original_heading.parent == body, "Original heading not in body"


@allure.epic("Book import")
@allure.feature("URL import: _add_source_info")
def test_add_source_info_no_body():
    """Test that _add_source_info works correctly with fragments without body tag."""
    # Create a mock instance that doesn't call the full initialization
    with patch.object(BookLoaderURL, "__init__", return_value=None):
        loader = BookLoaderURL()
        loader.url = "https://example.com/test-article"
        loader.meta = {
            MetadataField.TITLE: "Test Article Title",
            MetadataField.AUTHOR: "Test Author",
            MetadataField.LANGUAGE: "English",
        }

        # Test with just content, no body tag
        html_content = "<p>Simple paragraph.</p>"
        loader.text = html_content
        loader.book_start, loader.book_end = 0, len(loader.text)

        loader.tree_root = parse_partial_html(html_content)
        loader._add_source_info()
        result = etree_to_str(loader.tree_root)
        print(result)

        parsed_doc = etree.fromstring(result, etree.HTMLParser())

        # Look for the source-info div - it should exist somewhere in the document
        source_info_div = parsed_doc.xpath("//div[@class='source-info']")
        assert len(source_info_div) > 0, "Source info div not found in document"

        # Check the structure of the source-info div
        div = source_info_div[0]
        assert div.find("h1") is not None, "Title heading not found"
        assert div.find("h1").text == "Test Article Title", "Title text doesn't match"

        original_p = parsed_doc.xpath("//p[text()='Simple paragraph.']")
        assert len(original_p) > 0, "Original paragraph not found"


@allure.epic("Book import")
@allure.feature("URL import: extract_readable_html")
def test_extract_readable_html_aggressive():
    """Test that extract_readable_html with aggressive cleaning uses trafilatura correctly."""
    # Create a mock instance that doesn't call the full initialization
    with (
        patch.object(BookLoaderURL, "__init__", return_value=None),
        patch("trafilatura.extract") as mock_trafilatura,
    ):
        mock_trafilatura.return_value = "<div>Aggressively cleaned content</div>"

        loader = BookLoaderURL()
        loader.cleaning_level = CleaningLevel.AGGRESSIVE
        loader.html_content = "<html><body><div>Original content with junk</div></body></html>"
        loader.text = loader.html_content
        loader.book_start, loader.book_end = 0, len(loader.text)

        result = loader.extract_readable_html()

        mock_trafilatura.assert_called_once()
        call_kwargs = mock_trafilatura.call_args[1]
        assert call_kwargs["output_format"] == "html"
        assert call_kwargs["include_comments"] is False
        assert call_kwargs["favor_precision"] is True
        assert call_kwargs["favor_recall"] is False
        assert call_kwargs["deduplicate"] is True

        assert result == "<div>Aggressively cleaned content</div>"


@allure.epic("Book import")
@allure.feature("URL import: extract_readable_html")
def test_extract_readable_html_moderate():
    """Test that extract_readable_html with moderate cleaning uses trafilatura correctly."""
    # Create a mock instance that doesn't call the full initialization
    with (
        patch.object(BookLoaderURL, "__init__", return_value=None),
        patch("trafilatura.extract") as mock_trafilatura,
    ):
        mock_trafilatura.return_value = "<div>Moderately cleaned content</div>"

        loader = BookLoaderURL()
        loader.cleaning_level = CleaningLevel.MODERATE
        loader.html_content = "<html><body><div>Original content with some junk</div></body></html>"
        loader.text = loader.html_content
        loader.book_start, loader.book_end = 0, len(loader.text)

        result = loader.extract_readable_html()

        mock_trafilatura.assert_called_once()
        call_kwargs = mock_trafilatura.call_args[1]
        assert call_kwargs["output_format"] == "html"
        assert call_kwargs["include_comments"] is True
        assert call_kwargs["favor_precision"] is False
        assert call_kwargs["favor_recall"] is True
        assert call_kwargs["deduplicate"] is False

        assert result == "<div>Moderately cleaned content</div>"


@allure.epic("Book import")
@allure.feature("URL import: extract_readable_html")
def test_extract_readable_html_minimal():
    """Test that extract_readable_html with minimal cleaning returns original content."""
    # Create a mock instance that doesn't call the full initialization
    with (
        patch.object(BookLoaderURL, "__init__", return_value=None),
        patch("trafilatura.extract") as mock_trafilatura,
        patch("trafilatura.core.extract_metadata") as mock_extract_metadata,
    ):
        # Make sure trafilatura is not called for minimal cleaning
        mock_trafilatura.return_value = "<div>Cleaned content</div>"
        mock_extract_metadata.return_value = MagicMock(as_dict=lambda: {"title": "Test"})

        loader = BookLoaderURL()
        loader.cleaning_level = CleaningLevel.MINIMAL
        original_html = "<html><body><div>Original unmodified content</div></body></html>"
        loader.html_content = original_html
        loader.text = loader.html_content
        loader.book_start, loader.book_end = 0, len(loader.text)

        result = loader.extract_readable_html()

        mock_trafilatura.assert_not_called()
        assert result == original_html


@allure.epic("Book import")
@allure.feature("URL import: extract_readable_html")
def test_extract_readable_html_fallback():
    """Test that extract_readable_html falls back to original content when trafilatura fails."""
    # Create a mock instance that doesn't call the full initialization
    with (
        patch.object(BookLoaderURL, "__init__", return_value=None),
        patch("trafilatura.extract") as mock_trafilatura,
        patch("trafilatura.core.extract_metadata") as mock_extract_metadata,
        patch("lexiflux.ebook.book_loader_url.log.info") as mock_log,
    ):
        # Make trafilatura return None to force fallback
        mock_trafilatura.return_value = None
        mock_extract_metadata.return_value = MagicMock(as_dict=lambda: {"title": "Test"})

        loader = BookLoaderURL()
        loader.cleaning_level = CleaningLevel.MODERATE
        original_html = "<html><body><div>Original content for fallback</div></body></html>"
        loader.html_content = original_html
        loader.text = loader.html_content
        loader.book_start, loader.book_end = 0, len(loader.text)

        result = loader.extract_readable_html()

        mock_trafilatura.assert_called_once()
        mock_extract_metadata.assert_called_once()
        mock_log.assert_any_call("Using original HTML")

        assert result == original_html


@allure.epic("Book import")
@allure.feature("URL import: load_text")
def test_load_text_request_and_processing():
    """Test the entire load_text flow with mocked dependencies."""
    # Create a mock instance that doesn't call the full initialization
    with (
        patch.object(BookLoaderURL, "__init__", return_value=None),
        patch("requests.get") as mock_get,
        patch.object(BookLoaderURL, "extract_readable_html") as mock_extract,
        patch("lexiflux.ebook.book_loader_url.parse_partial_html") as mock_parse,
        patch("lexiflux.ebook.book_loader_url.refine_html") as mock_clear,
        patch.object(BookLoaderURL, "_add_source_info"),
    ):
        # Setup mock responses
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Test content</p></body></html>"
        mock_get.return_value = mock_response

        mock_extract.return_value = "<p>Extracted content</p>"

        tree_root = etree.fromstring("<html><body></body></html>", etree.HTMLParser())
        mock_parse.return_value = tree_root

        mock_clear.return_value = "<p>Cleaned content</p>"

        # Create and setup the loader
        loader = BookLoaderURL()
        loader.url = "https://example.com/test"
        loader.headers = {"User-Agent": "Test Agent"}
        loader.tree_root = None
        loader.text = ""
        loader.detect_meta = MagicMock()

        loader.load_text()

        # Verify the flow
        mock_get.assert_called_once_with(
            "https://example.com/test", headers={"User-Agent": "Test Agent"}, timeout=30
        )
        mock_extract.assert_called_once()
        mock_parse.assert_called()
        assert mock_parse.call_count == 2  # reparse afte trafilatura readable extract

        # Verify the final text
        assert loader.text == "<p>Cleaned content</p>"


@allure.epic("Book import")
@allure.feature("URL import: detect_meta")
def test_detect_meta_no_text_attribute():
    """Test that detect_meta works correctly when text attribute is not set."""
    with (
        patch.object(BookLoaderURL, "__init__", return_value=None),
        patch("lexiflux.ebook.book_loader_url.extract_web_page_metadata") as mock_metadata,
        patch.object(BookLoaderURL, "detect_language", return_value="English"),
    ):
        # Setup metadata
        metadata = {
            MetadataField.TITLE: "Test Article",
            MetadataField.AUTHOR: "Test Author",
            MetadataField.LANGUAGE: None,  # Set to None to test language detection
            MetadataField.RELEASED: None,
            MetadataField.CREDITS: None,
        }
        mock_metadata.return_value = metadata

        # Create a loader object but bypass initialization
        loader = BookLoaderURL()

        # Set up required attributes manually, but deliberately omit 'text'
        loader.url = "https://example.com/test"
        loader.html_content = "<html><body><p>Test content</p></body></html>"
        loader.anchor_map = {}
        loader.meta = {}

        # Create tree_root from the html_content
        from lxml import etree, html
        import io

        parser = etree.HTMLParser(recover=True, remove_comments=True, remove_pis=True)
        tree = html.parse(io.StringIO(loader.html_content), parser=parser)
        loader.tree_root = tree.getroot()

        # Call detect_meta - this should not raise an AttributeError
        result_meta, book_start, book_end = loader.detect_meta()

        assert result_meta[MetadataField.TITLE] == "Test Article"
        assert result_meta[MetadataField.AUTHOR] == "Test Author"
        assert result_meta[MetadataField.LANGUAGE] is None  # since text is not set
        assert book_start == 0
        assert book_end == 0  # Should be 0 since text is not set


@allure.epic("Book import")
@allure.feature("URL import: import_book view")
@patch("lexiflux.views.import_views.BookLoaderURL")
def test_import_book_from_url_success(mock_book_loader_url):
    """Test successful book import from URL."""

    request = MagicMock(spec=HttpRequest)
    request.method = "POST"  # Add method attribute for require_POST decorator
    request.user = MagicMock()
    request.user.email = "test@example.com"
    request.META = {}  # Add META for CSRF token processing
    request.POST = {
        "importType": "url",
        "url": "https://example.com/book",
        "cleaning_level": "moderate",
    }

    mock_book = MagicMock()
    mock_book.title = "Test Book from URL"
    mock_book_instance = MagicMock()
    mock_book_instance.create.return_value = mock_book
    mock_book_loader_url.return_value = mock_book_instance

    with (
        patch("lexiflux.views.import_views.render") as mock_render,
        patch("lexiflux.decorators.login_required", lambda f: f),
    ):  # Bypass decorator
        response = import_book(request)

    mock_book_loader_url.assert_called_once_with(
        "https://example.com/book", cleaning_level="moderate"
    )
    mock_book_instance.create.assert_called_once_with("test@example.com")
    mock_book.save.assert_called_once()

    assert "error_message" not in response.content.decode("utf-8")
    assert "show-edit-modal" in response.content.decode("utf-8")


@allure.epic("Book import")
@allure.feature("URL import: import_book view")
@patch("lexiflux.views.import_views.BookLoaderURL")
def test_import_book_from_url_with_aggressive_cleaning(mock_book_loader_url):
    """Test URL import with aggressive cleaning level."""
    request = MagicMock(spec=HttpRequest)
    request.method = "POST"  # Add method attribute for require_POST decorator
    request.user = MagicMock()
    request.user.email = "test@example.com"
    request.META = {}  # Add META for CSRF token processing
    request.POST = {
        "importType": "url",
        "url": "https://example.com/book",
        "cleaning_level": "aggressive",
    }

    mock_book = MagicMock()
    mock_book_instance = MagicMock()
    mock_book_instance.create.return_value = mock_book
    mock_book_loader_url.return_value = mock_book_instance

    with (
        patch("lexiflux.views.library_views.render"),
        patch("lexiflux.decorators.login_required", lambda f: f),
    ):  # Bypass decorator
        import_book(request)

    mock_book_loader_url.assert_called_once_with(
        "https://example.com/book", cleaning_level="aggressive"
    )


@allure.epic("Book import")
@allure.feature("URL import: import_book view")
def test_import_book_from_url_invalid_url():
    """Test handling of invalid URL during import."""
    request = MagicMock(spec=HttpRequest)
    request.method = "POST"  # Add method attribute for require_POST decorator
    request.user = MagicMock()
    request.META = {}  # Add META for CSRF token processing
    request.POST = {"importType": "url", "url": "not-a-valid-url", "cleaning_level": "moderate"}

    with (
        patch("lexiflux.views.import_views.render") as mock_render,
        patch("lexiflux.decorators.login_required", lambda f: f),
    ):  # Bypass decorator
        response = import_book(request)

    mock_render.assert_called_once()
    context = mock_render.call_args[0][2]
    assert "error_message" in context
    assert "Invalid URL format" in context["error_message"]


@allure.epic("Book import")
@allure.feature("URL import: import_book view")
@patch("django.core.validators.URLValidator")
def test_import_book_from_url_empty_url(mock_validator):
    """Test handling of empty URL during import."""
    request = MagicMock(spec=HttpRequest)
    request.method = "POST"  # Add method attribute for require_POST decorator
    request.user = MagicMock()
    request.META = {}  # Add META for CSRF token processing
    request.POST = {
        "importType": "url",
        "url": "",  # Empty URL
        "cleaning_level": "moderate",
    }

    with (
        patch("lexiflux.views.import_views.render") as mock_render,
        patch("lexiflux.decorators.login_required", lambda f: f),
    ):  # Bypass decorator
        response = import_book(request)

    mock_render.assert_called_once()
    context = mock_render.call_args[0][2]
    assert "error_message" in context
    assert "No URL provided" in context["error_message"]

    mock_validator.assert_not_called()


@allure.epic("Book import")
@allure.feature("Paste import: import_book view")
@patch("tempfile.NamedTemporaryFile")
@patch("lexiflux.views.import_views.BookLoaderPlainText")
def test_import_book_from_paste_text_success(mock_book_loader, mock_temp_file):
    """Test successful book import from pasted text content."""
    request = MagicMock(spec=HttpRequest)
    request.method = "POST"  # Add method attribute for require_POST decorator
    request.user = MagicMock()
    request.user.email = "test@example.com"
    request.META = {}  # Add META for CSRF token processing
    request.POST = {
        "importType": "paste",
        "pasted_content": "This is some pasted text content for the book.",
        "paste_format": "txt",
    }

    mock_file = MagicMock()
    mock_file.name = "/tmp/test_file.txt"
    mock_temp_file.return_value.__enter__.return_value = mock_file

    mock_book = MagicMock()
    mock_book.title = "Pasted Text Book"
    mock_book_instance = MagicMock()
    mock_book_instance.create.return_value = mock_book
    mock_book_loader.return_value = mock_book_instance

    with (
        patch("lexiflux.views.library_views.render"),
        patch("os.unlink"),
        patch("lexiflux.decorators.login_required", lambda f: f),
    ):  # Bypass decorator
        response = import_book(request)

    mock_file.write.assert_called_once_with(b"This is some pasted text content for the book.")

    mock_book_loader.assert_called_once_with(mock_file.name, original_filename="pasted_text.txt")

    mock_book_instance.create.assert_called_once_with("test@example.com")
    mock_book.save.assert_called_once()


@allure.epic("Book import")
@allure.feature("Paste import: import_book view")
@patch("tempfile.NamedTemporaryFile")
@patch("lexiflux.views.import_views.BookLoaderHtml")
def test_import_book_from_paste_html_success(mock_book_loader, mock_temp_file):
    """Test successful book import from pasted HTML content."""
    request = MagicMock(spec=HttpRequest)
    request.method = "POST"  # Add method attribute for require_POST decorator
    request.user = MagicMock()
    request.user.email = "test@example.com"
    request.META = {}  # Add META for CSRF token processing
    request.POST = {
        "importType": "paste",
        "pasted_content": "<html><body><h1>Book Title</h1><p>Content</p></body></html>",
        "paste_format": "html",
    }

    mock_file = MagicMock()
    mock_file.name = "/tmp/test_file.html"
    mock_temp_file.return_value.__enter__.return_value = mock_file

    mock_book = MagicMock()
    mock_book.title = "Pasted HTML Book"
    mock_book_instance = MagicMock()
    mock_book_instance.create.return_value = mock_book
    mock_book_loader.return_value = mock_book_instance

    with (
        patch("lexiflux.views.library_views.render"),
        patch("os.unlink"),
        patch("lexiflux.decorators.login_required", lambda f: f),
    ):  # Bypass decorator
        response = import_book(request)

    mock_book_loader.assert_called_once_with(
        mock_file.name, original_filename="pasted_content.html"
    )

    mock_book_instance.create.assert_called_once_with("test@example.com")
    mock_book.save.assert_called_once()


@allure.epic("Book import")
@allure.feature("Paste import: import_book view")
def test_import_book_from_paste_empty_content():
    """Test handling of empty pasted content during import."""
    request = MagicMock(spec=HttpRequest)
    request.method = "POST"  # Add method attribute for require_POST decorator
    request.user = MagicMock()
    request.META = {}  # Add META for CSRF token processing
    request.POST = {
        "importType": "paste",
        "pasted_content": "",  # Empty content
        "paste_format": "txt",
    }

    with (
        patch("lexiflux.views.import_views.render") as mock_render,
        patch("lexiflux.decorators.login_required", lambda f: f),
    ):  # Bypass decorator
        response = import_book(request)

    mock_render.assert_called_once()
    context = mock_render.call_args[0][2]
    assert "error_message" in context
    assert "No content pasted" in context["error_message"]


@allure.epic("Book import")
@allure.feature("Paste import: import_book view")
def test_import_book_from_paste_whitespace_only():
    """Test handling of whitespace-only pasted content during import."""
    request = MagicMock(spec=HttpRequest)
    request.method = "POST"  # Add method attribute for require_POST decorator
    request.user = MagicMock()
    request.META = {}  # Add META for CSRF token processing
    request.POST = {
        "importType": "paste",
        "pasted_content": "   \n  \t  ",  # Whitespace-only content
        "paste_format": "txt",
    }

    with (
        patch("lexiflux.views.import_views.render") as mock_render,
        patch("lexiflux.decorators.login_required", lambda f: f),
    ):  # Bypass decorator
        response = import_book(request)

    mock_render.assert_called_once()
    context = mock_render.call_args[0][2]
    assert "error_message" in context
    assert "No content pasted" in context["error_message"]


@allure.epic("Book import")
@allure.feature("Paste import: import_book view")
@patch("tempfile.NamedTemporaryFile")
def test_import_book_from_paste_file_cleanup(mock_temp_file):
    """Test that temporary files are cleaned up after paste import."""
    request = MagicMock(spec=HttpRequest)
    request.method = "POST"  # Add method attribute for require_POST decorator
    request.user = MagicMock()
    request.user.email = "test@example.com"
    request.META = {}  # Add META for CSRF token processing
    request.POST = {"importType": "paste", "pasted_content": "Test content", "paste_format": "txt"}

    mock_file = MagicMock()
    mock_file.name = "/tmp/test_file.txt"
    mock_temp_file.return_value.__enter__.return_value = mock_file

    # Mock os.unlink to verify it's called
    with (
        patch("lexiflux.views.import_views.BookLoaderPlainText") as mock_loader,
        patch("os.unlink") as mock_unlink,
        patch("lexiflux.views.library_views.render"),
        patch("lexiflux.decorators.login_required", lambda f: f),
    ):  # Bypass decorator
        # Setup book loader to return a book
        mock_book = MagicMock()
        mock_instance = MagicMock()
        mock_instance.create.return_value = mock_book
        mock_loader.return_value = mock_instance

        import_book(request)

    mock_unlink.assert_called_once_with(mock_file.name)


@allure.epic("Book import")
@allure.feature("Paste import: import_book view")
@patch("tempfile.NamedTemporaryFile")
def test_import_book_from_paste_with_exception_still_cleans_up(mock_temp_file):
    """Test that temporary files are cleaned up even if an exception occurs."""
    request = MagicMock(spec=HttpRequest)
    request.method = "POST"  # Add method attribute for require_POST decorator
    request.user = MagicMock()
    request.user.email = "test@example.com"
    request.META = {}  # Add META for CSRF token processing
    request.POST = {"importType": "paste", "pasted_content": "Test content", "paste_format": "txt"}

    mock_file = MagicMock()
    mock_file.name = "/tmp/test_file.txt"
    mock_temp_file.return_value.__enter__.return_value = mock_file

    # Mock BookLoaderPlainText to raise an exception
    with (
        patch("lexiflux.views.import_views.BookLoaderPlainText") as mock_loader,
        patch("os.unlink") as mock_unlink,
        patch("lexiflux.views.library_views.render"),
        patch("lexiflux.decorators.login_required", lambda f: f),
    ):  # Bypass decorator
        mock_loader.return_value.create.side_effect = ValueError("Test error")

        import_book(request)

    mock_unlink.assert_called_once_with(mock_file.name)


@allure.epic("Book import")
@allure.feature("General import: import_book view")
def test_import_book_unknown_type():
    """Test handling of unknown import type."""
    request = MagicMock(spec=HttpRequest)
    request.method = "POST"  # Add method attribute for require_POST decorator
    request.user = MagicMock()
    request.META = {}  # Add META for CSRF token processing
    request.POST = {
        "importType": "unknown_type"  # Invalid import type
    }

    with (
        patch("lexiflux.views.import_views.render") as mock_render,
        patch("lexiflux.decorators.login_required", lambda f: f),
    ):  # Bypass decorator
        response = import_book(request)

    mock_render.assert_called_once()
    context = mock_render.call_args[0][2]
    assert "error_message" in context
    assert "Unknown import type" in context["error_message"]


@pytest.mark.django_db
class TestImportIntegration:
    @allure.epic("Book import")
    @allure.feature("URL import: integration")
    @patch("lexiflux.views.import_views.BookLoaderURL")
    def test_url_import_integration(self, mock_book_loader_url, client, approved_user, book):
        """Test URL import flow with Django test client."""
        client.force_login(approved_user)

        # Set up mock book loader to return the existing book fixture
        mock_book_instance = MagicMock()
        mock_book_instance.create.return_value = book
        mock_book_loader_url.return_value = mock_book_instance

        response = client.post(
            "/api/import-book/",
            {
                "importType": "url",
                "url": "https://example.com/valid-book",
                "cleaning_level": "moderate",
            },
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 200
        assert b"show-edit-modal" in response.content
        assert b"error_message" not in response.content

        # Verify book loader was called correctly
        mock_book_loader_url.assert_called_once_with(
            "https://example.com/valid-book", cleaning_level="moderate"
        )
        mock_book_instance.create.assert_called_once_with(approved_user.email)

    @allure.epic("Book import")
    @allure.feature("Paste import: integration")
    def test_paste_import_integration(self, client, approved_user, book):
        """Test paste import flow with Django test client."""
        client.force_login(approved_user)

        with patch("lexiflux.views.import_views.BookLoaderPlainText") as mock_loader:
            # Set up mock loader to return the existing book fixture
            mock_instance = MagicMock()
            mock_instance.create.return_value = book
            mock_loader.return_value = mock_instance

            response = client.post(
                "/api/import-book/",
                {
                    "importType": "paste",
                    "pasted_content": "This is test content for a book import.",
                    "paste_format": "txt",
                },
                HTTP_HX_REQUEST="true",
            )

        assert response.status_code == 200
        assert b"show-edit-modal" in response.content
        assert b"error_message" not in response.content
