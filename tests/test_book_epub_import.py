from ebooklib import epub

from lexiflux.ebook.book_epub import flatten_list, extract_headings


def test_flatten_list_single_level():
    data = [{'Chapter 1': 'href1'}, {'Chapter 2': 'href2'}]
    expected = [{'Chapter 1': 'href1'}, {'Chapter 2': 'href2'}]
    assert flatten_list(data) == expected


def test_flatten_list_nested():
    data = [{'Chapter 1': [{'Section 1.1': 'href1-1'}, {'Section 1.2': 'href1-2'}]}, {'Chapter 2': 'href2'}]
    expected = [{'Chapter 1.Section 1.1': 'href1-1'}, {'Chapter 1.Section 1.2': 'href1-2'}, {'Chapter 2': 'href2'}]
    assert flatten_list(data) == expected


def test_extract_headings_with_links():
    epub_toc = [epub.Link("link_href", "Link Title")]
    expected = [{'Link Title': 'link_href'}]
    assert extract_headings(epub_toc) == expected


def test_extract_headings_nested():
    epub_toc = [(epub.Link("link_href", "Link Title"), [epub.Link("nested_link_href", "Nested Link")])]
    expected = [{'Link Title': [{'Nested Link': 'nested_link_href'}]}]
    assert extract_headings(epub_toc) == expected


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

# todo: e2e import-epub