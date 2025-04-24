import re

import allure
import pytest

from lexiflux.ebook.book_loader_epub import TARGET_PAGE_SIZE
from lexiflux.ebook.html_page_splitter import HtmlPageSplitter


@allure.epic("Book import")
@allure.feature("EPUB: parse pages")
def test_multiple_paragraphs_near_limit():
    """Test handling of multiple paragraphs near the page size limit."""
    content = """
    <div>
        <p>First paragraph with a complete sentence. Another sentence here.</p>
        <p>Second paragraph that contains several sentences. Here is one more. And another one.</p>
        <p>Third paragraph with some content. More text here. Final sentence.</p>
    </div>
    """
    target_size = 165

    medium_splitter = HtmlPageSplitter(content, target_page_size=target_size)
    pages = list(medium_splitter.pages())

    print(f"\nTotal content size: {len(content)} chars")
    print(f"Target page size: {target_size} chars")
    for i, page in enumerate(pages):
        print(f"Page {i + 1} size: {len(page)} chars")
        print(f"Page {i + 1} paragraph count: {page.count('</p>')}")
        print(f"Page {i + 1} content: {page}\n")

    assert len(pages) > 1, "Content should be split into multiple pages"

    for page in pages[:-1]:
        # Check page size
        assert len(page) <= target_size * 1.1, (
            f"Page size ({len(page)}) significantly exceeds target size ({target_size})"
        )
        # Verify complete paragraphs
        assert page.count("<p>") == page.count("</p>"), (
            "Paragraphs should not be split across pages"
        )
        # Verify sentence boundaries
        assert re.search(r"[.!?](\s|</p></div>|$)", page.strip()), (
            "Pages should end at sentence boundaries"
        )


@allure.epic("Book import")
@allure.feature("EPUB: parse pages")
class TestEpubContentSplitting:
    """Test suite for EPUB content splitting functionality."""

    def test_split_large_element(self):
        """Test splitting of large HTML elements."""
        large_html = (
            "<div><p>" + "HTML content " * 500 + "</p><p>" + "More HTML " * 500 + "</p></div>"
        )
        splitter = HtmlPageSplitter(large_html, target_page_size=TARGET_PAGE_SIZE)
        html_pages = list(splitter.pages())

        assert len(html_pages) > 1, "Large HTML element should be split into multiple pages"
        assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in html_pages), (
            "No HTML page should be more than twice the TARGET_PAGE_SIZE"
        )

        large_p_element = "<p>" + "Large content " * 1000 + "</p>"
        splitter = HtmlPageSplitter(large_p_element, target_page_size=TARGET_PAGE_SIZE)
        p_pages = list(splitter.pages())

        assert len(p_pages) > 1, "Large paragraph should be split into multiple pages"
        assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in p_pages), (
            "No paragraph page should be more than twice the TARGET_PAGE_SIZE"
        )

        print(f"HTML element pages: {len(html_pages)}: {[len(page) for page in html_pages]}")
        print(f"Large paragraph pages: {len(p_pages)}, sizes: {[len(page) for page in p_pages]}")

    def test_split_large_element_sentence_boundaries(self):
        """Test that content is split at sentence boundaries with realistic text."""
        target_size = 300

        russian_text = """
        <p class="p1">Моя мать не боялась загробной жизни. Как и большинство евреев, она имела очень смутное представление о том, что ждет человека, попавшего в могилу, и она старалась не думать об этом. Ее страшили само умирание, безвозвратность ухода из жизни. Я до сих пор не могу забыть, с какой одержимостью она говорила о неизбежности конца, особенно в моменты расставаний. Все мое существование было наполнено экзальтированными и драматическими сценами прощаний. И когда они с отцом уезжали из Бостона в Нью-Йорк на уик-энд, и когда мать провожала меня в летний лагерь, и даже когда я уходил в школу, она прижималась ко мне и со слезами говорила о том, как она ослабла, предупреждая, что мы можем больше не увидеться. Если мы шли вместе куда-нибудь, она вдруг останавливалась, словно теряя сознание. Иногда она показывала мне вену на шее, брала меня за руку и просила пощупать пульс, чтобы удостовериться в том, как неровно бьется ее сердце.</p>
        """
        splitter = HtmlPageSplitter(russian_text, target_page_size=target_size)

        pages = list(splitter.pages())

        # Print debug info
        print(f"\nText size: {len(russian_text)} chars")
        print(f"Target page size: {target_size} chars")
        for i, page in enumerate(pages):
            print(f"Page {i + 1}:\n{page}")

        # Verify we get multiple pages due to small target size
        assert len(pages) > 1, "Text should be split into multiple pages"

        # Check that each page (except possibly the last) is close to but not over target size
        for page in pages[:-1]:
            assert len(page) <= target_size * 1.1, (
                f"Page size ({len(page)}) significantly exceeds target size ({target_size})"
            )

        # Check that each page ends with a complete sentence
        sentence_endings = r"[.!?](\s|</p>|$)"
        for page in pages[:-1]:
            print(f"Page content: {page}")
            stripped_page = page.strip()
            assert re.search(sentence_endings, stripped_page), (
                f"Page should end with a complete sentence, but got: {stripped_page[-50:]}"
            )

    def test_very_long_single_sentence(self):
        """Test handling of sentences longer than page size."""
        target_size = 50

        long_sentence = "<p>This is a very long sentence that significantly exceeds our tiny page size limit and will need to be split into multiple pages somehow.</p>"
        splitter = HtmlPageSplitter(long_sentence, target_page_size=target_size)
        pages = list(splitter.pages())

        print(f"\nLong sentence size: {len(long_sentence)} chars")
        print(f"Target page size: {target_size} chars")
        for i, page in enumerate(pages):
            print(f"Page {i + 1}:\n{page}")

        assert len(pages) > 1, "Very long sentence should be split"
        assert all(len(page) <= target_size * 1.2 for page in pages[:-1]), (
            "Split pages should not significantly exceed target size"
        )

    def test_html_tag_integrity(self):
        """Test that HTML tags are never split across pages. Each page must be valid HTML."""
        target_size = 50

        complex_html = """
        <p>Start of text 
        <a href="../Text/chapter1.xhtml" class="very-long-class-name-to-force-splitting">
        This is a link with a very long text that should be split across pages but the tag itself should stay intact
        </a>
        <span class="another-long-class-that-should-not-be-split">
        More text that goes on and on and should also be split into multiple pages while preserving the HTML structure
        </span>
        </p>
        """
        splitter = HtmlPageSplitter(complex_html, target_page_size=target_size)
        pages = list(splitter.pages())

        print("\nSplit pages content:")
        for i, page in enumerate(pages):
            print(f"\nPage {i + 1}:")
            print(page)

        for i, page in enumerate(pages, 1):
            # Each page should be wrapped in the same set of parent tags as they appear in that position
            # in the original document (in this case, always <p>)
            assert page.lstrip().startswith("<p>"), f"Page {i} doesn't start with opening <p> tag"
            assert page.rstrip().endswith("</p>"), f"Page {i} doesn't end with closing </p> tag"

            # Stack to track tags opened in this page
            tag_stack = []

            # Find all tags in the page
            all_tags = re.finditer(r"</?[a-zA-Z][^>]*>", page)
            for tag_match in all_tags:
                tag = tag_match.group()
                if tag.startswith("</"):
                    # This is a closing tag
                    if not tag_stack:
                        pytest.fail(
                            f"Found closing tag {tag} without matching opening tag in page {i}"
                        )
                    if not tag[2:-1].lower() == tag_stack[-1].lower():
                        pytest.fail(
                            f"Closing tag {tag} doesn't match last opened tag {tag_stack[-1]} in page {i}"
                        )
                    tag_stack.pop()
                elif not tag.endswith("/>"):  # Ignore self-closing tags
                    # This is an opening tag
                    tag_name = re.match(r"<([a-zA-Z][^>\s]*)", tag).group(1)
                    tag_stack.append(tag_name)

            # At the end of the page, all tags should be closed
            assert len(tag_stack) == 0, f"Unclosed tags {tag_stack} at end of page {i}"

            # Make sure no HTML entities are split
            if "&" in page:
                parts = page.split("&")
                for part in parts[1:]:  # Skip first part (before any &)
                    assert ";" in part, f"Split HTML entity in page {i}"
