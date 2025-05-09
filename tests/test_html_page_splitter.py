import re

import allure
import pytest
from lxml import etree

from lexiflux.ebook.html_page_splitter import HtmlPageSplitter, TARGET_PAGE_SIZE
from lexiflux.ebook.html_page_splitter import SplitterContext


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
                <tr><th>Header 1</th><th>Header 2</th></tr>
                <tr><td>Cell 1</td><td>Cell 2 with longer content</td></tr>
                <tr><td>Cell 3 with long content</td><td>Cell 4</td></tr>
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

        assert len(pages) > 0, "Should produce at least one page even with malformed HTML"

        # Verify that the output pages can be parsed as HTML
        for page in pages:
            try:
                etree.fromstring(f"<root>{page}</root>", parser=etree.HTMLParser(recover=True))
            except Exception as e:
                pytest.fail(f"Failed to parse output page: {str(e)}")


def test_split_text_long_sentence_simplified():
    """Simplified test for splitting long text that ensures all content is preserved.
    Uses lxml for proper HTML parsing instead of regex.
    """
    from lxml import etree

    # Test content with a long sentence
    content = """
    <div>
        <span>Short span content</span>
        This is a very long sentence in the tail of the span element that significantly exceeds the tiny page size limit and must be split by words rather than sentences because it continues for a long time without any punctuation or breaks so it will force the code to enter the sentence-too-long condition in the _split_text method which needs to be tested specifically to ensure word-by-word splitting works properly.
        <p>Another paragraph after the long sentence.</p>
    </div>
    """
    target_size = 50  # Very small target to force splitting

    # Split the content
    splitter = HtmlPageSplitter(content, target_page_size=target_size)
    pages = list(splitter.pages())

    # Print the pages for visual inspection
    print(f"\nContent size: {len(content)} chars")
    print(f"Target page size: {target_size} chars")
    print(f"Number of pages: {len(pages)}")
    for i, page in enumerate(pages):
        print(f"Page {i + 1} size: {len(page)} chars")
        print(f"Page {i + 1} content: {page}\n")

    # Verify we have multiple pages
    assert len(pages) > 1, "Long content should be split into multiple pages"

    # Check page sizes (allow reasonable tolerance)
    for page in pages[:-1]:  # All pages except the last
        assert len(page) <= target_size * 2, (
            f"Page size ({len(page)}) significantly exceeds target size ({target_size})"
        )

    # Extract text content from the original HTML using lxml
    def get_text_content(html_string):
        # Parse HTML
        root = etree.fromstring(f"<root>{html_string}</root>", parser=etree.HTMLParser())

        # Extract all text (including element text and tail text)
        text_content = ""

        def extract_text(element):
            nonlocal text_content
            # Add element's text if it exists
            if element.text:
                text_content += element.text + " "

            # Process children
            for child in element:
                extract_text(child)

            # Add element's tail if it exists
            if element.tail:
                text_content += element.tail + " "

        extract_text(root)

        # Normalize whitespace and convert to lowercase
        return " ".join(text_content.split()).lower()

    # Get original text content and words
    original_text = get_text_content(content)
    original_words = set(original_text.split())

    # Extract text from all pages using lxml
    combined_text = get_text_content("".join(pages))
    output_words = set(combined_text.split())

    # Check that all words from original content are in output
    missing_words = original_words - output_words
    assert len(missing_words) == 0, f"All words should be preserved. Missing: {missing_words}"

    # Check for any extra words (might indicate duplication)
    extra_words = output_words - original_words
    assert len(extra_words) == 0, f"No extra words should be added. Extra: {extra_words}"

    # Additional debug info
    print(f"Original words count: {len(original_words)}")
    print(f"Output words count: {len(output_words)}")
    if missing_words:
        print(f"Missing words: {missing_words}")
    if extra_words:
        print(f"Extra words: {extra_words}")


@allure.epic("Book import")
@allure.feature("EPUB: parse pages")
def test_direct_split_text_method():
    """Test the _split_text method directly with a simple text comparison."""
    # Create a minimal HTML for testing
    html_content = "<div>test</div>"
    splitter = HtmlPageSplitter(html_content, target_page_size=10)  # Very small target size

    # Create very long text with individual words that exceed target page size
    long_text = "ThisIsAVeryLongWord ThatExceedsTargetSize AnotherLongWord AndSomeMoreText"

    # Create a context to pass to _split_text
    context = SplitterContext(size=0, chunks=[])

    # Add closing tag to force chunking
    closing_tag = "</div>"

    # Collect pages generated by _split_text
    generated_pages = []
    for page in splitter._split_text(context, long_text, closing_tag=closing_tag):
        generated_pages.append(page)
        assert len(page) <= splitter.target_page_size * 3, (
            f"Page size ({len(page)}) exceeds target size ({splitter.target_page_size})"
        )

    # Print the results for visual inspection
    print("\nDirect _split_text test:")
    print(f"Long text: '{long_text}'")
    print(f"Target page size: {splitter.target_page_size} chars")
    print(f"Number of pages: {len(generated_pages)}")
    for i, page in enumerate(generated_pages):
        print(f"Page {i + 1} size: {len(page)} chars")
        print(f"Page {i + 1} content: {page}\n")

    # Extract text from all pages
    combined_output = " ".join(generated_pages)
    output_text = combined_output.replace("<div>", "").replace("</div>", "").strip()

    assert output_text == long_text, "Output text should match input text"
