from unittest.mock import patch, MagicMock

import allure
import pytest
from ebooklib import epub, ITEM_DOCUMENT

from lexiflux.ebook.book_loader_epub import flatten_list, extract_headings, BookLoaderEpub, href_hierarchy, clear_html


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
@pytest.mark.django_db
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
@pytest.mark.django_db
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
@pytest.mark.django_db
def test_get_random_words_empty_book(book_epub):
    # Patch the pages method to return an empty book
    with patch.object(book_epub.epub, 'get_items', return_value=[]):
        result = book_epub.get_random_words(words_num=15)
        assert result == ''  # Should return an empty string for an empty book
