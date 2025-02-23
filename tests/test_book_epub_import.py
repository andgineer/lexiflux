from unittest.mock import patch, MagicMock

import allure
import pytest
from ebooklib import epub, ITEM_DOCUMENT, ITEM_IMAGE

from lexiflux.ebook.book_loader_epub import (
    flatten_list,
    extract_headings,
    BookLoaderEpub,
    href_hierarchy,
    clear_html,
    TARGET_PAGE_SIZE,
)


@allure.epic("Book import")
@allure.feature("EPUB: Flatten list")
def test_flatten_list_single_level():
    data = [{"Chapter 1": "href1"}, {"Chapter 2": "href2"}]
    expected = [{"Chapter 1": "href1"}, {"Chapter 2": "href2"}]
    assert flatten_list(data) == expected


@allure.epic("Book import")
@allure.feature("EPUB: Flatten list")
def test_flatten_list_nested():
    data = [
        {"Chapter 1": [{"Section 1.1": "href1-1"}, {"Section 1.2": "href1-2"}]},
        {"Chapter 2": "href2"},
    ]
    expected = [
        {"Chapter 1.Section 1.1": "href1-1"},
        {"Chapter 1.Section 1.2": "href1-2"},
        {"Chapter 2": "href2"},
    ]
    assert flatten_list(data) == expected


@allure.epic("Book import")
@allure.feature("EPUB: Headings extraction")
def test_extract_headings_with_links():
    epub_toc = [epub.Link("link_href", "Link Title")]
    expected = [{"Link Title": "link_href"}]
    assert extract_headings(epub_toc) == expected


@allure.epic("Book import")
@allure.feature("EPUB: Headings extraction")
def test_extract_headings_nested():
    epub_toc = [
        (epub.Link("link_href", "Link Title"), [epub.Link("nested_link_href", "Nested Link")])
    ]
    expected = [{"Link Title": [{"Nested Link": "nested_link_href"}]}]
    assert extract_headings(epub_toc) == expected


@allure.epic("Book import")
@allure.feature("EPUB: Headings extraction")
def test_extract_headings_with_sections_and_subchapters():
    c1 = epub.Link("chap1.xhtml", "Chapter 1", "chap1")
    c2 = epub.Link("chap2.xhtml", "Chapter 2", "chap2")
    epub_toc = (
        epub.Link("intro.xhtml", "Introduction", "intro"),
        (epub.Section("Languages"), (c1, c2)),
    )
    expected = [
        {"Introduction": "intro.xhtml"},
        {"Languages": [{"Chapter 1": "chap1.xhtml"}, {"Chapter 2": "chap2.xhtml"}]},
    ]
    assert extract_headings(epub_toc) == expected


@allure.epic("Book import")
@allure.feature("EPUB: Import command")
@pytest.mark.django_db
def test_import_epub_e2e():
    book = BookLoaderEpub("tests/resources/genius.epub").create("")
    assert book.title == "The Genius"
    assert book.author.name == "Theodore Dreiser"
    assert book.language.name == "English"
    assert book.public is True
    assert book.pages.count() == 735


@allure.epic("Book import")
@allure.feature("EPUB: Headings extraction")
def test_epub_import_href_hierarchy():
    input_dict = {
        "title.xml": "Title",
        "main2.xml": "Part 1 - YOUTH.Chapter 1",
        "main2.xml#anchor": "Part 1 - YOUTH.Chapter 2",
    }
    expected_output = {
        "title.xml": {"#": "Title"},
        "main2.xml": {"#": "Part 1 - YOUTH.Chapter 1", "#anchor": "Part 1 - YOUTH.Chapter 2"},
    }
    assert href_hierarchy(input_dict) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_head():
    input_html = "<html><head><title>Test</title></head><body><p>Hello, world!</p></body></html>"
    expected_output = "<p>Hello, world!</p>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_unwraps_tags():
    input_html = "<html><body><span><p>Hello, world!</p></span></body></html>"
    expected_output = "<span><p>Hello, world!</p></span>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_attributes():
    input_html = '<div class="test"><p style="color: red;">Hello, world!</p></div>'
    expected_output = "<div><p>Hello, world!</p></div>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_handles_empty_input():
    input_html = ""
    expected_output = ""
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_get_random_words_epub(book_epub):
    MAX_ATTEMPTS = 5
    WORDS_NUM = 15

    for _ in range(MAX_ATTEMPTS):
        random_words_1 = book_epub.get_random_words(words_num=WORDS_NUM)
        random_words_2 = book_epub.get_random_words(words_num=WORDS_NUM)

        assert len(random_words_1.split()) == WORDS_NUM
        # assert all(word.startswith('word') or word.startswith('Page') for word in random_words_1.split())

        from pprint import pprint

        pprint(random_words_1)
        pprint(random_words_2)
        if random_words_1 != random_words_2:
            # Test passes if we find different results
            return

    # If we get here, the test failed all attempts
    pytest.fail(f"get_random_words returned the same result in {MAX_ATTEMPTS} attempts")


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_get_random_words_short_book(book_epub):
    # Patch the pages method to return a short book
    short_items = [
        MagicMock(
            get_body_content=lambda: " ".join([f"word{i}" for i in range(10)]).encode("utf-8"),
            get_type=lambda: ITEM_DOCUMENT,
        )
        for _ in range(3)
    ]
    with patch.object(book_epub.epub, "get_items", return_value=short_items):
        result = book_epub.get_random_words(words_num=15)
        assert 3 <= len(result.split()) <= 10  # Should return between 3 and 10 words
        assert all(word.startswith("word") for word in result.split())


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_get_random_words_empty_book(book_epub):
    # Patch the pages method to return an empty book
    with patch.object(book_epub.epub, "get_items", return_value=[]):
        result = book_epub.get_random_words(words_num=15)
        assert result == ""  # Should return an empty string for an empty book


@allure.epic("Book import")
@allure.feature("EPUB: parse pages")
def test_pages_basic_functionality(book_epub):
    pages = list(book_epub.pages())
    assert len(pages) > 0
    assert all(isinstance(page, str) for page in pages)


@allure.epic("Book import")
@allure.feature("EPUB: parse pages")
def test_pages_content_splitting(book_epub):
    # Test with normal HTML content
    html_content = (
        "<div><p>" + ("HTML content " * 500) + "</p><p>" + ("More HTML " * 500) + "</p></div>"
    )
    book_epub.epub.get_items()[0].get_body_content = lambda: html_content.encode("utf-8")

    html_pages = list(book_epub.pages())

    assert len(html_pages) > 1, "HTML content should be split into multiple pages"
    assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in html_pages), (
        "No HTML page should be more than twice the TARGET_PAGE_SIZE"
    )

    # Test with content that looks like plain text but is actually in a <p> tag
    plain_text_like_content = "<p>" + ("Simple HTML content " * 1000) + "</p>"
    book_epub.epub.get_items()[0].get_body_content = lambda: plain_text_like_content.encode("utf-8")

    text_like_pages = list(book_epub.pages())

    assert len(text_like_pages) > 1, "Simple HTML content should be split into multiple pages"
    assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in text_like_pages), (
        "No simple HTML page should be more than twice the TARGET_PAGE_SIZE"
    )

    # Test with content without any HTML tags
    no_tags_content = "Plain text content without any HTML tags. " * 1000
    book_epub.epub.get_items()[0].get_body_content = lambda: no_tags_content.encode("utf-8")

    no_tags_pages = list(book_epub.pages())

    print(f"HTML pages: {len(html_pages)}, sizes: {[len(page) for page in html_pages]}")
    print(
        f"Simple HTML pages: {len(text_like_pages)}, sizes: {[len(page) for page in text_like_pages]}"
    )
    print(f"No tags pages: {len(no_tags_pages)}, sizes: {[len(page) for page in no_tags_pages]}")

    assert len(no_tags_pages) > 1, "Content without tags should be split into multiple pages"
    assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in no_tags_pages), (
        "No page of content without tags should be more than twice the TARGET_PAGE_SIZE"
    )


@pytest.fixture
def medium_page_size(monkeypatch):
    """Set medium page size for testing multiple paragraphs."""
    monkeypatch.setattr("lexiflux.ebook.book_loader_epub.TARGET_PAGE_SIZE", 200)
    return 200


@allure.epic("Book import")
@allure.feature("EPUB: parse pages")
def test_pages_with_anchors(book_epub):
    # Modify the last item (page_19.xhtml) to have an anchor
    content = "<h1 id='chapter1'>Chapter 1</h1><p>Content</p>"
    mock_item = book_epub.epub.get_items()[-1]  # Use the last item from the fixture
    mock_item.get_body_content = lambda: content.encode("utf-8")

    # Update heading_hrefs to match the actual item name
    book_epub.heading_hrefs = {"page_19.xhtml": {"#chapter1": "Chapter 1"}}

    # Process pages
    pages = list(book_epub.pages())

    # Debug print statements
    print("Anchor map:", book_epub.anchor_map)
    print("Heading hrefs:", book_epub.heading_hrefs)

    # Check if the anchor is in the anchor_map
    expected_key = "page_19.xhtml#chapter1"
    assert expected_key in book_epub.anchor_map, (
        f"Expected key '{expected_key}' not found in anchor_map"
    )

    # Assert on the content of the anchor_map entry
    assert book_epub.anchor_map[expected_key]["item_name"] == "page_19.xhtml", (
        "Item name in anchor map does not match expected value"
    )
    assert book_epub.anchor_map[expected_key]["page"] == 20, (
        "Page number in anchor map does not match expected value"
    )
    assert book_epub.anchor_map[expected_key]["item_id"] == "item_19", (
        "Item ID in anchor map does not match expected value"
    )

    # Check if the file entry is also in the anchor_map
    assert "page_19.xhtml" in book_epub.anchor_map, "File entry not found in anchor_map"

    # Print the actual anchor_map for debugging
    print("Final anchor_map:", book_epub.anchor_map)


@allure.epic("Book import")
@allure.feature("EPUB: parse pages")
def test_pages_empty_content(book_epub):
    # Modify all items to have empty content
    for item in book_epub.epub.get_items():
        item.get_body_content = lambda: b""

    pages = list(book_epub.pages())
    assert len(pages) == 0


@allure.epic("Book import")
@allure.feature("EPUB: parse pages")
def test_pages_non_document_item(book_epub):
    # Modify one item to be a non-document item
    book_epub.epub.get_items()[0].get_type = lambda: ITEM_IMAGE

    pages = list(book_epub.pages())
    assert len(pages) < 20  # We should have fewer pages than the original 20


@allure.epic("Book import")
@allure.feature("EPUB: parse pages")
def test_pages_with_toc_processing(book_epub):
    # Set up a simple TOC structure
    book_epub.heading_hrefs = {"page_0.xhtml": {"#": "Chapter 1"}}

    list(book_epub.pages())  # Process pages
    assert book_epub.toc == [("Chapter 1", 1, 0)]


@allure.epic("Book import")
@allure.feature("EPUB: parse pages")
@patch("lexiflux.ebook.book_loader_epub.clear_html")
def test_pages_with_html_cleaning(mock_clear_html, book_epub):
    mock_clear_html.return_value = "Cleaned content"

    pages = list(book_epub.pages())
    assert all(page == "Cleaned content" for page in pages)
    assert mock_clear_html.call_count == 20  # Called for each of the 20 pages


@allure.epic("Book import")
@allure.feature("EPUB: parse pages")
def test_process_toc(book_epub):
    book_epub.heading_hrefs = {
        "page_0.xhtml": {"#": "Chapter 1", "#section1": "Section 1"},
        "page_1.xhtml": {"#": "Chapter 2"},
    }
    book_epub.anchor_map = {
        "page_0.xhtml": {"page": 1, "item_id": "item_0", "item_name": "page_0.xhtml"},
        "page_0.xhtml#section1": {"page": 2, "item_id": "item_0", "item_name": "page_0.xhtml"},
        "page_1.xhtml": {"page": 3, "item_id": "item_1", "item_name": "page_1.xhtml"},
    }

    book_epub._process_toc()
    assert book_epub.toc == [("Chapter 1", 1, 0), ("Section 1", 2, 0), ("Chapter 2", 3, 0)]


@allure.epic("Book import")
@allure.feature("EPUB: Title extraction")
def test_extract_title_with_headers(book_epub_loader):
    content = """
    <html>
        <head><title>Main Title</title></head>
        <body>
            <h1>Main Header</h1>
            <h2>Subheader</h2>
            <div class="title">
                <p>Author Name</p>
                <p>Book Title</p>
            </div>
        </body>
    </html>
    """
    mock_item = MagicMock(get_body_content=lambda: content.encode("utf-8"))

    loader = book_epub_loader
    extracted_title = loader.extract_title(mock_item)
    assert extracted_title == "Main Title", (
        "The title should be extracted from the <title> tag in <head>"
    )


@allure.epic("Book import")
@allure.feature("EPUB: Title extraction")
def test_extract_title_with_div_class_title(book_epub_loader):
    content = """
    <html>
        <body>
            <div class="title">
                <p>Author Name</p>
                <p>Book Title</p>
            </div>
        </body>
    </html>
    """
    mock_item = MagicMock(get_body_content=lambda: content.encode("utf-8"))

    loader = book_epub_loader
    extracted_title = loader.extract_title(mock_item)
    assert extracted_title == "Author Name Book Title", (
        "The title should be concatenated from nested <p> tags in <div class='title'>"
    )


@allure.epic("Book import")
@allure.feature("EPUB: Title extraction")
def test_extract_title_with_headers_and_no_div(book_epub_loader):
    content = """
    <html>
        <body>
            <h1>Main Header</h1>
            <h2>Subheader</h2>
        </body>
    </html>
    """
    mock_item = MagicMock(get_body_content=lambda: content.encode("utf-8"))

    loader = book_epub_loader
    extracted_title = loader.extract_title(mock_item)
    assert extracted_title == "Main Header", "The title should be extracted from the first <h1> tag"


@allure.epic("Book import")
@allure.feature("EPUB: Title extraction")
def test_extract_title_no_title_or_headers(book_epub_loader):
    content = """
    <html>
        <body>
            <p>Some random content</p>
        </body>
    </html>
    """
    mock_item = MagicMock(get_body_content=lambda: content.encode("utf-8"))

    loader = book_epub_loader
    extracted_title = loader.extract_title(mock_item)
    assert extracted_title is None, "No title should be extracted when no suitable tags are found"


@allure.epic("Book import")
@allure.feature("EPUB: Title extraction")
def test_extract_title_handles_malformed_html(book_epub_loader):
    content = """
    <html>
        <head><title>  Main Title   </title></head>
        <body>
                <p>   Author Name  </p>
                <p>   Book Title  </p>
    """  # Missing closing tags
    mock_item = MagicMock(get_body_content=lambda: content.encode("utf-8"))

    loader = book_epub_loader
    extracted_title = loader.extract_title(mock_item)
    assert extracted_title == "Main Title", (
        "The title should still be extracted from the <title> tag despite malformed HTML"
    )


@allure.epic("Book import")
@allure.feature("EPUB: TOC extraction")
def test_generate_toc_fallback_to_spine_item_name(book_epub_loader):
    # Mock EPUB item without valid title in the body
    content_no_title = """
    <html>
        <body>
            <p>Some random content without a proper title</p>
        </body>
    </html>
    """
    mock_item = MagicMock(
        get_body_content=lambda: content_no_title.encode("utf-8"),
        get_name=lambda: "chapter1.xhtml",  # Mock the get_name() method
        file_name="chapter1.xhtml",  # Mock the file_name attribute
        get_type=lambda: ITEM_DOCUMENT,  # Ensure the item is treated as a document
    )

    mock_epub = MagicMock()
    mock_epub.spine = [("item_1", None)]  # Simulate one item in the spine
    mock_epub.get_item_with_id.return_value = mock_item

    # Patch the loader to use the mocked EPUB
    with patch("lexiflux.ebook.book_loader_epub.epub.read_epub", return_value=mock_epub):
        loader = book_epub_loader
        loader.epub = mock_epub  # Assign the mocked EPUB

        # Generate the TOC from the spine
        generated_toc = loader.generate_toc_from_spine()

        # Expected TOC should use the spine item's name without extension
        expected_toc = {"chapter1.xhtml": {"#": "chapter1"}}

        assert generated_toc == expected_toc, (
            f"Expected TOC {expected_toc}, but got {generated_toc}."
        )


@allure.epic("Book import")
@allure.feature("EPUB: TOC extraction")
def test_generate_toc_from_spine_when_toc_is_empty(book_epub_loader):
    # Mock an EPUB object with an empty TOC and a spine
    mock_epub = MagicMock()
    mock_epub.toc = []  # Empty TOC
    mock_epub.spine = [("item_1", None), ("item_2", None)]

    mock_items = {
        "item_1": MagicMock(
            get_name=lambda: "chapter1.xhtml",
            get_type=lambda: ITEM_DOCUMENT,
            file_name="chapter1.xhtml",
            get_body_content=lambda: "<h1>Chapter 1</h1>".encode("utf-8"),
        ),
        "item_2": MagicMock(
            get_name=lambda: "chapter2.xhtml",
            get_type=lambda: ITEM_DOCUMENT,
            file_name="chapter2.xhtml",
            get_body_content=lambda: "<h1>Chapter 2</h1>".encode("utf-8"),
        ),
    }
    mock_epub.get_item_with_id.side_effect = lambda x: mock_items[x]

    # Patch the BookLoaderEpub object to use the mocked EPUB
    with patch("lexiflux.ebook.book_loader_epub.epub.read_epub", return_value=mock_epub):
        loader = book_epub_loader
        loader.epub = mock_epub  # Simulate loading the mocked EPUB

        # Trigger the TOC generation
        generated_toc = loader.generate_toc_from_spine()

        # Validate the output
        expected_toc = {
            "chapter1.xhtml": {"#": "Chapter 1"},
            "chapter2.xhtml": {"#": "Chapter 2"},
        }

        assert generated_toc == expected_toc, "TOC should be generated from spine when TOC is empty"
