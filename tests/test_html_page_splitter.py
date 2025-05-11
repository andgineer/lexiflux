import re

import allure
import pytest
from lxml import etree

from lexiflux.ebook.html_page_splitter import HtmlPageSplitter, TARGET_PAGE_SIZE


def html_to_normalized_text(html: str):
    html_text = etree.tostring(
        etree.fromstring(html.encode("utf-8"), parser=etree.HTMLParser()),
        method="text",
        encoding="unicode",
    )
    text_normalized = " ".join(html_text.split())
    print(f"Input normalized text:\n{text_normalized}")
    return text_normalized


def pages_to_normalized_text(pages):
    """Extract text from all pages and combine"""
    parser = etree.HTMLParser(recover=True)
    all_page_texts = []
    for page in pages:
        page_tree = etree.fromstring(page.encode("utf-8"), parser)
        page_text = etree.tostring(page_tree, method="text", encoding="unicode")
        all_page_texts.append(page_text)
    pages_text = " ".join(all_page_texts)
    text_normalized = " ".join(pages_text.split())
    print(f"Pages normalized text:\n{text_normalized}")
    return text_normalized


def assert_text(html: str, pages: list):
    input_text = html_to_normalized_text(html)
    pages_text = pages_to_normalized_text(pages)
    assert input_text == pages_text, "Pages should preserve all input text"


def assert_html_text_len(html_str: str, max_len: float) -> None:
    tree = etree.fromstring(html_str, parser=etree.HTMLParser())
    assert len(etree.tostring(tree, method="text", encoding="unicode")) <= max_len, (
        f"HTML text length ({len(etree.tostring(tree, method='text', encoding='unicode'))}) "
        f"exceeds maximum length ({max_len})"
    )


@allure.epic("Book import")
@allure.feature("HTML split pages")
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

    assert_text(content, pages)

    for page in pages[:-1]:
        page_tree = etree.fromstring(page.encode("utf-8"), parser=etree.HTMLParser())
        assert (
            len(etree.tostring(page_tree, method="text", encoding="unicode")) <= target_size * 1.25
        ), f"Page size ({len(page)}) significantly exceeds target size ({target_size})"
        # Verify complete paragraphs
        assert page.count("<p>") == page.count("</p>"), (
            "Paragraphs should not be split across pages"
        )
        # Verify sentence boundaries
        assert re.search(r"[.!?](\s|</p></div>|$)", page.strip()), (
            "Pages should end at sentence boundaries"
        )


@allure.epic("Book import")
@allure.feature("HTML split pages")
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

        assert_text(large_html, html_pages)

        large_p_element = "<p>" + "Large content " * 1000 + "</p>"
        splitter = HtmlPageSplitter(large_p_element, target_page_size=TARGET_PAGE_SIZE)
        p_pages = list(splitter.pages())

        assert len(p_pages) > 1, "Large paragraph should be split into multiple pages"
        assert all(len(page) <= TARGET_PAGE_SIZE * 2 for page in p_pages), (
            "No paragraph page should be more than twice the TARGET_PAGE_SIZE"
        )

        print(f"HTML element pages: {len(html_pages)}: {[len(page) for page in html_pages]}")
        print(f"Large paragraph pages: {len(p_pages)}, sizes: {[len(page) for page in p_pages]}")

        assert_text(large_p_element, p_pages)

    def test_split_large_element_sentence_boundaries(self):
        """Test that content is split at sentence boundaries with realistic text."""
        target_size = 300
        tolerance = 0.4

        russian_text = """
        <p class="p1">Моя мать не боялась загробной жизни. Как и большинство евреев, она имела очень смутное представление о том, что ждет человека, попавшего в могилу, и она старалась не думать об этом. Ее страшили само умирание, безвозвратность ухода из жизни. Я до сих пор не могу забыть, с какой одержимостью она говорила о неизбежности конца, особенно в моменты расставаний. Все мое существование было наполнено экзальтированными и драматическими сценами прощаний. И когда они с отцом уезжали из Бостона в Нью-Йорк на уик-энд, и когда мать провожала меня в летний лагерь, и даже когда я уходил в школу, она прижималась ко мне и со слезами говорила о том, как она ослабла, предупреждая, что мы можем больше не увидеться. Если мы шли вместе куда-нибудь, она вдруг останавливалась, словно теряя сознание. Иногда она показывала мне вену на шее, брала меня за руку и просила пощупать пульс, чтобы удостовериться в том, как неровно бьется ее сердце.</p>
        """
        splitter = HtmlPageSplitter(
            russian_text, target_page_size=target_size, page_size_tolerance=tolerance
        )

        pages = list(splitter.pages())

        # Print debug info
        print(f"\nText size: {len(russian_text)} chars")
        print(f"Target page size: {target_size} chars")
        for i, page in enumerate(pages):
            print(f"Page {i + 1}:\n{page}")

        # Verify we get multiple pages due to small target size
        assert len(pages) > 1, "Text should be split into multiple pages"

        for page in pages:
            assert_html_text_len(page, target_size * (1 + tolerance))

        # Check that each page ends with a complete sentence
        sentence_endings = r"[.!?](\s|</p>|$)"
        for page in pages[:-1]:
            print(f"Page content: {page}")
            stripped_page = page.strip()
            assert re.search(sentence_endings, stripped_page), (
                f"Page should end with a complete sentence, but got: {stripped_page[-50:]}"
            )

        assert_text(russian_text, pages)

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

        assert_text(long_sentence, pages)

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

        assert_text(complex_html, pages)

    def test_nested_elements(self):
        """Test splitting content with deeply nested elements."""
        target_size = 100

        # Create deeply nested HTML structure
        nested_html = "<div><section><article><div><p>"
        nested_html += "Deeply nested content " * 30
        nested_html += "</p></div></article></section></div>"

        splitter = HtmlPageSplitter(nested_html, target_page_size=target_size)
        pages = list(splitter.pages())

        print(f"\nNested HTML size: {len(nested_html)} chars")
        print(f"Target page size: {target_size} chars")
        for i, page in enumerate(pages):
            print(f"Page {i + 1} size: {len(page)} chars")
            print(f"Page {i + 1} content: {page[:100]}...")

        assert len(pages) > 1, "Deeply nested content should be split into multiple pages"

        # Verify tag integrity - each page should maintain proper HTML structure
        for page in pages:
            # Parse the page to check if it's valid HTML
            try:
                etree.fromstring(f"<root>{page}</root>", parser=etree.HTMLParser())
            except etree.ParseError as e:
                pytest.fail(f"Page is not valid HTML: {str(e)}")

        assert_text(nested_html, pages)

    def test_empty_and_whitespace_content(self):
        """Test handling of empty or whitespace-only content."""
        # Empty content
        empty_splitter = HtmlPageSplitter("", target_page_size=100)
        empty_pages = list(empty_splitter.pages())
        assert len(empty_pages) == 0, "Empty content should produce no pages"

        # Whitespace only content
        whitespace_splitter = HtmlPageSplitter("  \n  \t  ", target_page_size=100)
        whitespace_pages = list(whitespace_splitter.pages())
        assert len(whitespace_pages) <= 1, "Whitespace-only content should produce at most one page"

        # Content with only HTML tags but no text
        empty_tags_html = "<div><p></p><span></span></div>"
        empty_tags_splitter = HtmlPageSplitter(empty_tags_html, target_page_size=100)
        empty_tags_pages = list(empty_tags_splitter.pages())
        assert len(empty_tags_pages) <= 1, "Empty tags should produce at most one page"

    def test_html_entities(self):
        """Test handling of HTML entities during splitting."""
        target_size = 50

        # HTML with entities
        html_with_entities = """
        <p>This text contains HTML entities like &amp; and &lt; and &gt; and &quot;
        which should never be split across pages. Even long entities like &longrightarrow;
        must be kept intact when splitting content into multiple pages.</p>
        """

        splitter = HtmlPageSplitter(html_with_entities, target_page_size=target_size)
        pages = list(splitter.pages())

        print(f"\nHTML with entities size: {len(html_with_entities)} chars")
        print(f"Target page size: {target_size} chars")
        for i, page in enumerate(pages):
            print(f"Page {i + 1}: {page}")

        # Check that no HTML entities are split
        for page in pages:
            # Find all ampersands in the page
            ampersand_positions = [m.start() for m in re.finditer("&", page)]

            for pos in ampersand_positions:
                # Find the semicolon that closes this entity
                semicolon_pos = page.find(";", pos)

                # Make sure each ampersand has a corresponding semicolon
                assert semicolon_pos != -1, (
                    f"HTML entity starting with & at position {pos} is not closed in page: {page}"
                )

        assert_text(html_with_entities, pages)

    def test_mixed_content_types(self):
        """Test splitting content with mixed element types (text, lists, tables, etc.)."""
        target_size = 300

        mixed_html = """
        <div>
            <h1>Mixed Content Test</h1>
            <p>This is a paragraph with regular text content that might need to be split.</p>
            <ul>
                <li>List item 1 with some text content</li>
                <li>List item 2 with additional text</li>
                <li>List item 3 with even more text content to increase size</li>
            </ul>
            <table>
                <tr><th>Header 1</th> <th>Header 2</th></tr>
                <tr><td>Cell 1</td> <td>Cell 2 with longer content</td></tr>
                <tr><td>Cell 3 with long content</td> <td>Cell 4</td></tr>
            </table>
            <p>Another paragraph after the table with more text content for splitting.</p>
        </div>
        """

        splitter = HtmlPageSplitter(mixed_html, target_page_size=target_size)
        pages = list(splitter.pages())

        print(f"\nMixed HTML size: {len(mixed_html)} chars")
        print(f"Target page size: {target_size} chars")
        for i, page in enumerate(pages):
            print(f"Page {i + 1} size: {len(page)} chars")

        assert len(pages) > 1, "Mixed content should be split into multiple pages"

        # Verify each page contains complete elements
        for page in pages:
            # Check list items integrity
            assert page.count("<li>") == page.count("</li>"), (
                "List items should not be split across pages"
            )

            # Check table row integrity
            assert page.count("<tr>") == page.count("</tr>"), (
                "Table rows should not be split across pages"
            )

            # Check table cell integrity
            assert page.count("<td>") == page.count("</td>"), (
                "Table cells should not be split across pages"
            )
            assert page.count("<th>") == page.count("</th>"), (
                "Table header cells should not be split across pages"
            )

        assert_text(mixed_html, pages)

    def test_content_with_images(self):
        """Test handling of content with image elements."""
        target_size = 250

        html_with_images = """
        <div>
            <p>Text before image.</p>
            <img src="image1.jpg" alt="Image 1" class="large" style="width:100%;">
            <p>Text between images with enough content to potentially split across pages. Text between images with enough content to potentially split across pages.Text between images with enough content to potentially split across pages.</p>
            <img src="image2.jpg" alt="Image 2" width="500" height="300">
            <p>Text after images with more content.</p>
        </div>
        """

        splitter = HtmlPageSplitter(html_with_images, target_page_size=target_size)
        pages = list(splitter.pages())

        print(f"\nHTML with images size: {len(html_with_images)} chars")
        print(f"Target page size: {target_size} chars")
        for i, page in enumerate(pages):
            print(f"Page {i + 1}:\n{page}")

        # Use BeautifulSoup to verify image integrity
        from bs4 import BeautifulSoup

        # Parse original HTML and extract image details
        original_soup = BeautifulSoup(html_with_images, "html.parser")
        original_images = original_soup.find_all("img")
        expected_image_count = len(original_images)

        # Store original image attributes for later comparison
        original_image_attrs = []
        for img in original_images:
            original_image_attrs.append(img.attrs)

        # Count images in split pages
        found_images = []
        for page in pages:
            page_soup = BeautifulSoup(page, "html.parser")
            page_images = page_soup.find_all("img")
            for img in page_images:
                found_images.append(img)

        # Verify all images are accounted for
        assert len(found_images) == expected_image_count, (
            f"Expected {expected_image_count} images, but found {len(found_images)} across all pages"
        )

        # Check that each image retains its original attributes
        for i, original_attrs in enumerate(original_image_attrs):
            # Find corresponding image in results by matching src attribute
            matching_images = [
                img for img in found_images if img.get("src") == original_attrs.get("src")
            ]
            assert len(matching_images) == 1, (
                f"Image with src={original_attrs.get('src')} was not found exactly once"
            )

            result_img = matching_images[0]
            # Check that all original attributes are preserved
            for attr_name, attr_value in original_attrs.items():
                assert result_img.has_attr(attr_name), (
                    f"Image missing {attr_name} attribute: {result_img}"
                )
                assert result_img[attr_name] == attr_value, (
                    f"Image attribute {attr_name} changed from '{attr_value}' to '{result_img[attr_name]}'"
                )

        assert_text(html_with_images, pages)

    def test_large_content_with_small_target(self):
        """Test extremely large content with a very small target page size."""
        target_size = 100  # Very small target size

        # Generate large HTML content
        large_content = "<div>"
        for i in range(50):
            large_content += (
                f"<p>Paragraph {i} with some text content. " + "More text. " * 10 + "</p>"
            )
        large_content += "</div>"

        splitter = HtmlPageSplitter(large_content, target_page_size=target_size)
        pages = list(splitter.pages())

        print(f"\nLarge content size: {len(large_content)} chars")
        print(f"Target page size: {target_size} chars")
        print(f"Number of pages: {len(pages)}")

        assert len(pages) > len(large_content) // target_size // 2, (
            "Should create many pages for large content"
        )

        # Check that page sizes are reasonable
        max_page_size = max(len(page) for page in pages)
        assert max_page_size <= target_size * 2, (
            f"Largest page size ({max_page_size}) exceeds twice the target size"
        )

        assert_text(large_content, pages)

    def test_unicode_content(self):
        """Test handling of content with Unicode characters from various scripts."""
        target_size = 200

        unicode_html = """
        <div>
            <p>English text with regular ASCII characters.</p>
            <p>Chinese text: 这是一些中文文本，应该正确处理。</p>
            <p>Arabic text: هذا نص باللغة العربية يجب معالجته بشكل صحيح.</p>
            <p>Russian text: Это текст на русском языке, который должен обрабатываться правильно.</p>
            <p>Emojis: 🌍 🌎 🌏 👨‍👩‍👧‍👦 should be handled correctly.</p>
            <p>Math symbols: ∑ ∫ ∞ √ ∆ should be preserved.</p>
        </div>
        """

        splitter = HtmlPageSplitter(unicode_html, target_page_size=target_size)
        pages = list(splitter.pages())

        print(f"\nUnicode HTML size: {len(unicode_html)} chars")
        print(f"Target page size: {target_size} chars")
        for i, page in enumerate(pages):
            print(f"Page {i + 1} size: {len(page)} chars")

        # Check that all Unicode content is preserved
        joined_content = "".join(pages)

        assert "这是一些中文文本" in joined_content, "Chinese text should be preserved"
        assert "هذا نص باللغة العربية" in joined_content, "Arabic text should be preserved"
        assert "Это текст на русском языке" in joined_content, "Russian text should be preserved"
        assert "🌍" in joined_content, "Emojis should be preserved"
        assert "∫" in joined_content, "Math symbols should be preserved"

        assert_text(unicode_html, pages)

    def test_malformed_html(self):
        """Test handling of malformed HTML content."""
        target_size = 150

        # Malformed HTML with unclosed tags and mismatched tags
        malformed_html = """
        <div>
            <p>This paragraph is not properly closed.
            <strong>This is bold text that's not closed.
            <em>This is emphasized text.</p>
            <span>This span has no closing tag.
            <p>Another paragraph with <a href="link.html">a link that's not closed</p>
        </div>
        """

        # Should not raise exceptions with malformed HTML
        splitter = HtmlPageSplitter(malformed_html, target_page_size=target_size)
        pages = list(splitter.pages())

        print(f"\nMalformed HTML size: {len(malformed_html)} chars")
        print(f"Target page size: {target_size} chars")
        for i, page in enumerate(pages):
            print(f"Page {i + 1}:\n{page}")

        assert pages, "Should produce at least one page even with malformed HTML"

        # Verify that the output pages can be parsed as HTML
        for page in pages:
            try:
                etree.fromstring(f"<root>{page}</root>", parser=etree.HTMLParser(recover=True))
            except Exception as e:
                pytest.fail(f"Failed to parse output page: {str(e)}")

        assert_text(malformed_html, pages)


@allure.epic("Book import")
@allure.feature("HTML split pages")
def test_split_text_long_sentence_simplified():
    """Test that ensures all content is preserved and in the correct order."""
    from lxml import etree

    # Test content with a long sentence in the tail
    content = """
    <div>
        <span>Short span content</span>
        This is a very long sentence in the tail of the span element that significantly exceeds the tiny page size limit and must be split by words rather than sentences because it continues for a long time without any punctuation or breaks so it will force the code to enter the sentence-too-long condition in the _split_text method which needs to be tested specifically to ensure word-by-word splitting works properly.
        <p>Another paragraph after the long sentence.</p>
    </div>
    """
    target_size = 50  # Very small target to force splitting

    # Parse the original content to extract text
    parser = etree.HTMLParser(recover=True)
    original_tree = etree.fromstring(content.encode("utf-8"), parser)

    # Split the content
    splitter = HtmlPageSplitter(content, target_page_size=target_size)
    pages = list(splitter.pages())

    # Print the pages for visual inspection
    print(f"\nContent size: {len(content)} chars")
    print(f"Target page size: {target_size} chars")
    print(f"Number of pages: {len(pages)}")
    for i, page in enumerate(pages):
        print(f"Page {i + 1} size: {len(page)} chars")
        print(f"Page {i + 1} content: {page}")

    assert_text(content, pages)

    # Also check that we have multiple pages
    assert len(pages) > 1, "Long content should be split into multiple pages"

    for page in pages:
        assert_html_text_len(page, target_size * 2)


@allure.epic("Book import")
@allure.feature("HTML split pages")
def test_direct_split_text_method():
    """Test the _split_text method directly with a simple text comparison."""
    # Create a minimal HTML for testing
    html_content = "<div>test</div>"

    # Very small target size with tolerance enough to find word boundaries
    splitter = HtmlPageSplitter(html_content, target_page_size=10, page_size_tolerance=1.5)

    # Create very long text with individual words that exceed target page size
    long_text = "ThisIsAVeryLongWord ThatExceedsTargetSize AnotherLongWord AndSomeMoreText"

    # Test the _split_text method directly
    text_chunks = splitter._split_text(long_text)

    # Print the results for visual inspection
    print("\nDirect _split_text test:")
    print(f"Long text: '{long_text}'")
    print(f"Target page size: {splitter.target_page_size} chars")
    print(f"Number of chunks: {len(text_chunks)}")
    for i, chunk in enumerate(text_chunks):
        print(f"Chunk {i + 1} size: {len(chunk)} chars")
        print(f"Chunk {i + 1} content: {chunk}\n")

    # Verify all text is preserved
    combined_text = "".join(text_chunks)
    assert combined_text == long_text, "Split text should preserve all content"

    assert len(text_chunks) == 5, "With target size 10, we should have 5 chunks"


@allure.epic("Book import")
@allure.feature("HTML split pages")
def test_preserve_empty_tags():
    """Test that tags with no text content (like img, br, hr) are preserved during splitting."""
    target_size = 100

    html_with_empty_tags = """
    <div>
        <p>Text before image.</p>
        <img src="image1.jpg" alt="First Image" />
        <p>Text after image.</p>
        <br />
        <hr />
        <p>Text after break and horizontal rule.</p>
        <input type="text" name="test" />
        <meta charset="UTF-8" />
        <p>More text content that might cause splitting.</p>
        <img src="image2.jpg" alt="Second Image" width="200" height="100" />
        <br />
        <p>Final paragraph with more content to exceed the page size limit and force splitting across multiple pages.</p>
    </div>
    """

    # Parse original HTML to count empty tags
    parser = etree.HTMLParser(recover=True)
    original_tree = etree.fromstring(html_with_empty_tags.encode("utf-8"), parser)

    # Count original empty tags
    empty_tags = ["img", "br", "hr", "input", "meta"]
    original_counts = {}
    for tag in empty_tags:
        original_counts[tag] = len(original_tree.xpath(f".//{tag}"))

    print(f"\nOriginal tag counts: {original_counts}")

    # Split the content
    splitter = HtmlPageSplitter(html_with_empty_tags, target_page_size=target_size)
    pages = list(splitter.pages())

    print(f"Target page size: {target_size} chars")
    print(f"Number of pages: {len(pages)}")

    # Count empty tags in all pages
    combined_counts = {tag: 0 for tag in empty_tags}
    for i, page in enumerate(pages):
        print(f"\nPage {i + 1}:\n{page}")

        page_tree = etree.fromstring(page.encode("utf-8"), parser)
        for tag in empty_tags:
            count = len(page_tree.xpath(f".//{tag}"))
            combined_counts[tag] += count
            if count > 0:
                print(f"  Found {count} {tag} tag(s)")

    print(f"\nTotal counts after splitting: {combined_counts}")

    # Verify all empty tags are preserved
    for tag in empty_tags:
        assert combined_counts[tag] == original_counts[tag], (
            f"Lost {tag} tags during splitting: original={original_counts[tag]}, "
            f"after split={combined_counts[tag]}"
        )

    # Also verify specific attributes are preserved
    # Check that img tags retain their attributes
    original_imgs = original_tree.xpath(".//img")
    all_split_imgs = []
    for page in pages:
        page_tree = etree.fromstring(page.encode("utf-8"), parser)
        all_split_imgs.extend(page_tree.xpath(".//img"))

    assert len(all_split_imgs) == len(original_imgs), "Number of img tags should be preserved"

    # Check that attributes are preserved for each img
    for orig_img in original_imgs:
        src = orig_img.get("src")
        matching_imgs = [img for img in all_split_imgs if img.get("src") == src]
        assert len(matching_imgs) == 1, f"Image with src={src} should appear exactly once"

        # Check all attributes are preserved
        for attr, value in orig_img.attrib.items():
            assert matching_imgs[0].get(attr) == value, (
                f"Attribute {attr} not preserved for img with src={src}"
            )

    assert_text(html_with_empty_tags, pages)


@allure.epic("Book import")
@allure.feature("HTML split pages")
def test_empty_tags_edge_cases():
    """Test edge cases for empty tags preservation."""
    target_size = 50

    # Test with empty tags at various positions
    edge_case_html = """
    <div>
        <br />  <!-- Empty tag at start -->
        <p>Small text.</p>
        <img src="test.jpg" />  <!-- Empty tag in middle -->
        <p>More text content here that might cause splitting.</p>
        <hr />  <!-- Empty tag at potential split point -->
        <p>Final text content.</p>
        <br />  <!-- Empty tag at end -->
    </div>
    """

    splitter = HtmlPageSplitter(edge_case_html, target_page_size=target_size)
    pages = list(splitter.pages())

    # Count br and hr tags in original and split content
    parser = etree.HTMLParser(recover=True)
    original_tree = etree.fromstring(edge_case_html.encode("utf-8"), parser)

    original_br_count = len(original_tree.xpath(".//br"))
    original_hr_count = len(original_tree.xpath(".//hr"))
    original_img_count = len(original_tree.xpath(".//img"))

    split_br_count = 0
    split_hr_count = 0
    split_img_count = 0

    for page in pages:
        page_tree = etree.fromstring(page.encode("utf-8"), parser)
        split_br_count += len(page_tree.xpath(".//br"))
        split_hr_count += len(page_tree.xpath(".//hr"))
        split_img_count += len(page_tree.xpath(".//img"))

    assert split_br_count == original_br_count, "BR tags should be preserved"
    assert split_hr_count == original_hr_count, "HR tags should be preserved"
    assert split_img_count == original_img_count, "IMG tags should be preserved"

    assert_text(edge_case_html, pages)

    # Test with multiple empty tags together
    multiple_empty_html = """
    <div>
        <p>Text before multiple empty tags.</p>
        <br /><br /><hr /><img src="test.jpg" /><br />
        <p>Text after multiple empty tags.</p>
    </div>
    """

    splitter2 = HtmlPageSplitter(multiple_empty_html, target_page_size=target_size)
    pages2 = list(splitter2.pages())

    # Verify the sequence of empty tags is maintained
    print(f"\nMultiple empty tags test:\n{pages2}")
    combined_html = "".join(pages2)
    assert '<br><br><hr><img src="test.jpg"><br>' in combined_html.replace("\n", ""), (
        "Sequence of empty tags should be preserved"
    )

    assert_text(multiple_empty_html, pages2)
