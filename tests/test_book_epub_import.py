import allure
import pytest
from ebooklib import epub

from lexiflux.ebook.book_epub import flatten_list, extract_headings, BookEpub, href_hierarchy, clear_html
from lexiflux.ebook.book_base import import_book


@allure.epic('Books import: EPUB')
@allure.feature('Flatten list')
def test_flatten_list_single_level():
    data = [{'Chapter 1': 'href1'}, {'Chapter 2': 'href2'}]
    expected = [{'Chapter 1': 'href1'}, {'Chapter 2': 'href2'}]
    assert flatten_list(data) == expected


@allure.epic('Books import: EPUB')
@allure.feature('Flatten list')
def test_flatten_list_nested():
    data = [{'Chapter 1': [{'Section 1.1': 'href1-1'}, {'Section 1.2': 'href1-2'}]}, {'Chapter 2': 'href2'}]
    expected = [{'Chapter 1.Section 1.1': 'href1-1'}, {'Chapter 1.Section 1.2': 'href1-2'}, {'Chapter 2': 'href2'}]
    assert flatten_list(data) == expected


@allure.epic('Books import: EPUB')
@allure.feature('Headings extraction')
def test_extract_headings_with_links():
    epub_toc = [epub.Link("link_href", "Link Title")]
    expected = [{'Link Title': 'link_href'}]
    assert extract_headings(epub_toc) == expected


@allure.epic('Books import: EPUB')
@allure.feature('Headings extraction')
def test_extract_headings_nested():
    epub_toc = [(epub.Link("link_href", "Link Title"), [epub.Link("nested_link_href", "Nested Link")])]
    expected = [{'Link Title': [{'Nested Link': 'nested_link_href'}]}]
    assert extract_headings(epub_toc) == expected


@allure.epic('Books import: EPUB')
@allure.feature('Headings extraction')
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


@allure.epic('Books import: EPUB')
@allure.feature('Import command')
@pytest.mark.django_db
def test_import_epub_e2e():
    book = import_book(BookEpub('tests/resources/genius.epub'), '')
    assert book.title == "The Genius"
    assert book.author.name == 'Theodore Dreiser'
    assert book.language.name == 'English'
    assert book.public is True
    assert book.pages.count() == 111
    with open('tests/resources/genius_1st_page.txt', 'r', encoding="utf8") as f:
        assert book.pages.first().content == f.read()
    expected_toc = [
        ['CHAPTER I.   Down the Rabbit-Hole', 1, 86],
        ['CHAPTER II.   The Pool of Tears', 6, 34],
        ['CHAPTER III.   A Caucus-Race and a Long Tale', 10, 135],
        ['CHAPTER IV.   The Rabbit Sends in a Little Bill', 14, 100],
        ['CHAPTER V.   Advice from a Caterpillar', 19, 264],
        ['CHAPTER VI.   Pig and Pepper', 24, 264],
        ['CHAPTER VII.   A Mad Tea-Party', 30, 169],
        ['CHAPTER VIII.   The Queen’s Croquet-Ground', 35, 400],
        ['CHAPTER IX.   The Mock Turtle’s Story', 41, 236],
        ['CHAPTER X.   The Lobster Quadrille', 46, 346],
        ['CHAPTER XI.   Кто украл the Tarts?', 51, 275],
        ['CHAPTER XII.   Alice’s Evidence', 56, 2],
    ]
    # assert book.toc == expected_toc


@allure.epic('Books import: EPUB')
@allure.feature('Headings extraction')
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


@allure.epic('Books import: EPUB')
@allure.feature('Clean HTML')
def test_clean_html_removes_head():
    input_html = "<html><head><title>Test</title></head><body><p>Hello, world!</p></body></html>"
    expected_output = "<p>Hello, world!</p>"
    assert clear_html(input_html) == expected_output


@allure.epic('Books import: EPUB')
@allure.feature('Clean HTML')
def test_clean_html_unwraps_tags():
    input_html = "<html><body><span><p>Hello, world!</p></span></body></html>"
    expected_output = "<p>Hello, world!</p>"
    assert clear_html(input_html) == expected_output


@allure.epic('Books import: EPUB')
@allure.feature('Clean HTML')
def test_clean_html_removes_attributes():
    input_html = '<div class="test"><p style="color: red;">Hello, world!</p></div>'
    expected_output = "<p>Hello, world!</p>"
    assert clear_html(input_html) == expected_output


@allure.epic('Books import: EPUB')
@allure.feature('Clean HTML')
def test_clean_html_handles_empty_input():
    input_html = ""
    expected_output = ""
    assert clear_html(input_html) == expected_output
