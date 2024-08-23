from unittest.mock import patch, MagicMock

import allure
import pytest
from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_DOCUMENT, ITEM_IMAGE

from lexiflux.ebook.book_loader_epub import flatten_list, extract_headings, BookLoaderEpub, href_hierarchy, clear_html, \
    TARGET_PAGE_SIZE


@allure.epic('Book import')
@allure.feature('EPUB: Flatten list')
def test_flatten_list_single_level():
    data = [{'Chapter 1': 'href1'}, {'Chapter 2': 'href2'}]
    expected = [{'Chapter 1': 'href1'}, {'Chapter 2': 'href2'}]
    assert flatten_list(data) == expected


@allure.epic('Book import')
@allure.feature('EPUB: Flatten list')
def test_flatten_list_nested():
    data = [{'Chapter 1': [{'Section 1.1': 'href1-1'}, {'Section 1.2': 'href1-2'}]}, {'Chapter 2': 'href2'}]
    expected = [{'Chapter 1.Section 1.1': 'href1-1'}, {'Chapter 1.Section 1.2': 'href1-2'}, {'Chapter 2': 'href2'}]
    assert flatten_list(data) == expected


@allure.epic('Book import')
@allure.feature('EPUB: Headings extraction')
def test_extract_headings_with_links():
    epub_toc = [epub.Link("link_href", "Link Title")]
    expected = [{'Link Title': 'link_href'}]
    assert extract_headings(epub_toc) == expected


@allure.epic('Book import')
@allure.feature('EPUB: Headings extraction')
def test_extract_headings_nested():
    epub_toc = [(epub.Link("link_href", "Link Title"), [epub.Link("nested_link_href", "Nested Link")])]
    expected = [{'Link Title': [{'Nested Link': 'nested_link_href'}]}]
    assert extract_headings(epub_toc) == expected


@allure.epic('Book import')
@allure.feature('EPUB: Headings extraction')
def test_extract_headings_with_sections_and_subchapters():
    c1 = epub.Link('chap1.xhtml', 'Chapter 1', 'chap1')
    c2 = epub.Link('chap2.xhtml', 'Chapter 2', 'chap2')
    epub_toc = (
        epub.Link('intro.xhtml', 'Introduction', 'intro'),
        (
            epub.Section('Languages'),
            (c1, c2)
        )
    )
    expected = [
        {'Introduction': 'intro.xhtml'},
        {'Languages': [
            {'Chapter 1': 'chap1.xhtml'},
            {'Chapter 2': 'chap2.xhtml'}
        ]}
    ]
    assert extract_headings(epub_toc) == expected


@allure.epic('Book import')
@allure.feature('EPUB: Import command')
@pytest.mark.django_db
def test_import_epub_e2e():
    book = BookLoaderEpub('tests/resources/genius.epub').create('')
    assert book.title == "The Genius"
    assert book.author.name == 'Theodore Dreiser'
    assert book.language.name == 'English'
    assert book.public is True
    assert book.pages.count() == 719


@allure.epic('Book import')
@allure.feature('EPUB: Headings extraction')
def test_epub_import_href_hierarchy():
    input_dict = {
        'title.xml': 'Title',
        'main2.xml': 'Part 1 - YOUTH.Chapter 1',
        'main2.xml#anchor': 'Part 1 - YOUTH.Chapter 2'
    }
    expected_output = {
        'title.xml': {"#": 'Title'},
        'main2.xml': {
            "#": 'Part 1 - YOUTH.Chapter 1',
            "#anchor": 'Part 1 - YOUTH.Chapter 2'
        }
    }
    assert href_hierarchy(input_dict) == expected_output


@allure.epic('Book import')
@allure.feature('EPUB: Clean HTML')
def test_clean_html_removes_head():
    input_html = "<html><head><title>Test</title></head><body><p>Hello, world!</p></body></html>"
    expected_output = "<p>Hello, world!</p>"
    assert clear_html(input_html) == expected_output


@allure.epic('Book import')
@allure.feature('EPUB: Clean HTML')
def test_clean_html_unwraps_tags():
    input_html = "<html><body><span><p>Hello, world!</p></span></body></html>"
    expected_output = "<p>Hello, world!</p>"
    assert clear_html(input_html) == expected_output


@allure.epic('Book import')
@allure.feature('EPUB: Clean HTML')
def test_clean_html_removes_attributes():
    input_html = '<div class="test"><p style="color: red;">Hello, world!</p></div>'
    expected_output = "<p>Hello, world!</p>"
    assert clear_html(input_html) == expected_output


@allure.epic('Book import')
@allure.feature('EPUB: Clean HTML')
def test_clean_html_handles_empty_input():
    input_html = ""
    expected_output = ""
    assert clear_html(input_html) == expected_output


@allure.epic('Book import')
@allure.feature('EPUB: Clean HTML')
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


@allure.epic('Book import')
@allure.feature('EPUB: Clean HTML')
def test_get_random_words_short_book(book_epub):
    # Patch the pages method to return a short book
    short_items = [
        MagicMock(
            get_body_content=lambda: ' '.join([f'word{i}' for i in range(10)]).encode("utf-8"),
            get_type=lambda: ITEM_DOCUMENT
        )
        for _ in range(3)
    ]
    with patch.object(book_epub.epub, 'get_items', return_value=short_items):
        result = book_epub.get_random_words(words_num=15)
        assert 3 <= len(result.split()) <= 10  # Should return between 3 and 10 words
        assert all(word.startswith('word') for word in result.split())


@allure.epic('Book import')
@allure.feature('EPUB: Clean HTML')
def test_get_random_words_empty_book(book_epub):
    # Patch the pages method to return an empty book
    with patch.object(book_epub.epub, 'get_items', return_value=[]):
        result = book_epub.get_random_words(words_num=15)
        assert result == ''  # Should return an empty string for an empty book


def test_pages_basic_functionality(book_epub):
    pages = list(book_epub.pages())
    assert len(pages) > 0
    assert all(isinstance(page, str) for page in pages)


def test_pages_content_splitting(book_epub):
    # Test with normal HTML content
    html_content = "<div><p>" + ("HTML content " * 500) + "</p><p>" + ("More HTML " * 500) + "</p></div>"
    book_epub.epub.get_items()[0].get_body_content = lambda: html_content.encode('utf-8')

    html_pages = list(book_epub.pages())

    assert len(html_pages) > 1, "HTML content should be split into multiple pages"
    assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in
               html_pages), "No HTML page should be more than twice the TARGET_PAGE_SIZE"

    # Test with content that looks like plain text but is actually in a <p> tag
    plain_text_like_content = "<p>" + ("Simple HTML content " * 1000) + "</p>"
    book_epub.epub.get_items()[0].get_body_content = lambda: plain_text_like_content.encode('utf-8')

    text_like_pages = list(book_epub.pages())

    assert len(text_like_pages) > 1, "Simple HTML content should be split into multiple pages"
    assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in
               text_like_pages), "No simple HTML page should be more than twice the TARGET_PAGE_SIZE"

    # Test with content without any HTML tags
    no_tags_content = "Plain text content without any HTML tags. " * 1000
    book_epub.epub.get_items()[0].get_body_content = lambda: no_tags_content.encode('utf-8')

    no_tags_pages = list(book_epub.pages())

    print(f"HTML pages: {len(html_pages)}, sizes: {[len(page) for page in html_pages]}")
    print(f"Simple HTML pages: {len(text_like_pages)}, sizes: {[len(page) for page in text_like_pages]}")
    print(f"No tags pages: {len(no_tags_pages)}, sizes: {[len(page) for page in no_tags_pages]}")

    assert len(no_tags_pages) > 1, "Content without tags should be split into multiple pages"
    assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in
               no_tags_pages), "No page of content without tags should be more than twice the TARGET_PAGE_SIZE"


def test_split_large_element(book_epub):
    # Test with a large HTML element
    large_html_element = BeautifulSoup(
        "<div><p>" + "HTML content " * 500 + "</p><p>" + "More HTML " * 500 + "</p></div>", "html.parser").div
    html_pages = list(book_epub._split_large_element(large_html_element))

    assert len(html_pages) > 1, "Large HTML element should be split into multiple pages"
    assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in
               html_pages), "No HTML page should be more than twice the TARGET_PAGE_SIZE"

    # Test with a large <p> element (simulating a large paragraph of text)
    large_p_element = BeautifulSoup("<p>" + "Large content " * 1000 + "</p>", "html.parser").p
    p_pages = list(book_epub._split_large_element(large_p_element))

    assert len(p_pages) > 1, "Large paragraph should be split into multiple pages"
    assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in
               p_pages), "No paragraph page should be more than twice the TARGET_PAGE_SIZE"

    # Test with content without any HTML tags
    no_tags_content = "Plain text content without any HTML tags. " * 1000
    no_tags_pages = list(book_epub._split_large_element(no_tags_content))

    print(f"HTML element pages: {len(html_pages)}, sizes: {[len(page) for page in html_pages]}")
    print(f"Large paragraph pages: {len(p_pages)}, sizes: {[len(page) for page in p_pages]}")
    print(f"No tags pages: {len(no_tags_pages)}, sizes: {[len(page) for page in no_tags_pages]}")

    assert len(no_tags_pages) > 1, "Content without tags should be split into multiple pages"
    assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in
               no_tags_pages), "No page of content without tags should be more than twice the TARGET_PAGE_SIZE"


def test_pages_with_anchors(book_epub):
    # Modify one item to have an anchor
    content = "<h1 id='chapter1'>Chapter 1</h1><p>Content</p>"
    book_epub.epub.get_items()[0].get_body_content = lambda: content.encode('utf-8')
    book_epub.epub.get_items()[0].file_name = "test.xhtml"
    book_epub.heading_hrefs = {"test.xhtml": {"#chapter1": "Chapter 1"}}

    list(book_epub.pages())  # Process pages
    assert "test.xhtml#chapter1" in book_epub.anchor_map
    assert "test.xhtml" in book_epub.anchor_map


def test_pages_empty_content(book_epub):
    # Modify all items to have empty content
    for item in book_epub.epub.get_items():
        item.get_body_content = lambda: b""

    pages = list(book_epub.pages())
    assert len(pages) == 0


def test_pages_non_document_item(book_epub):
    # Modify one item to be a non-document item
    book_epub.epub.get_items()[0].get_type = lambda: ITEM_IMAGE

    pages = list(book_epub.pages())
    assert len(pages) < 20  # We should have fewer pages than the original 20


def test_pages_with_toc_processing(book_epub):
    # Set up a simple TOC structure
    book_epub.heading_hrefs = {"page_0.xhtml": {"#": "Chapter 1"}}

    list(book_epub.pages())  # Process pages
    assert book_epub.toc == [("Chapter 1", 1, 0)]


@patch('lexiflux.ebook.book_loader_epub.clear_html')
def test_pages_with_html_cleaning(mock_clear_html, book_epub):
    mock_clear_html.return_value = "Cleaned content"

    pages = list(book_epub.pages())
    assert all(page == "Cleaned content" for page in pages)
    assert mock_clear_html.call_count == 20  # Called for each of the 20 pages


def test_process_toc(book_epub):
    book_epub.heading_hrefs = {
        "page_0.xhtml": {"#": "Chapter 1", "#section1": "Section 1"},
        "page_1.xhtml": {"#": "Chapter 2"}
    }
    book_epub.anchor_map = {
        "page_0.xhtml": {"page": 1, "item_id": "item_0", "item_name": "page_0.xhtml"},
        "page_0.xhtml#section1": {"page": 2, "item_id": "item_0", "item_name": "page_0.xhtml"},
        "page_1.xhtml": {"page": 3, "item_id": "item_1", "item_name": "page_1.xhtml"}
    }

    book_epub._process_toc()
    assert book_epub.toc == [
        ("Chapter 1", 1, 0),
        ("Section 1", 2, 0),
        ("Chapter 2", 3, 0)
    ]
