import re

import pytest
import allure
from bs4 import BeautifulSoup

from lexiflux.ebook.clear_html import clear_html, ALLOWED_TAGS, KEEP_EMPTY_TAGS, REMOVE_WITH_CONTENT


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
@pytest.mark.parametrize(
    "test_id, input_html, expected_output",
    [
        # Basic structure cleaning tests
        (
            "remove_head",
            "<html><head><title>Test</title></head><body><p>Hello, world!</p></body></html>",
            "<p>Hello, world!</p>",
        ),
        (
            "escape_unknown_tags",
            '<header class=""><section class="header-top py-1">some header</section>in header</header>',
            "some headerin header",
        ),
        (
            "unwraps_tags",
            "<html><body><span><p>Hello, world!</p></span></body></html>",
            "<span><p>Hello, world!</p></span>",
        ),
        (
            "remove_script_tags",
            "<div><script>alert('test');</script><p>Content</p></div>",
            "<div><p>Content</p></div>",
        ),
        (
            "remove_style_tags",
            "<div><style>.test { color: red; }</style><p>Content</p></div>",
            "<div><p>Content</p></div>",
        ),
        (
            "remove_iframe",
            "<div><iframe src='https://example.com'></iframe><p>Content</p></div>",
            "<div><p>Content</p></div>",
        ),
        (
            "web page",
            """            
            <!DOCTYPE html>
            <html>
            <head>
                <title>Tag Links Page</title>
            </head>
            <body>
                <h1>Page with Tag Links</h1>
                <a rel="tag" href="/tag/test">Test Tag</a>
                <a rel="tag" href="/tag/metadata">Metadata Tag</a>
            </body>
            </html>
            """,
            """<h1 class="display-4 fw-semibold text-primary mb-4">Page with Tag Links</h1> <a rel="tag" href="/tag/test">Test Tag</a> <a rel="tag" href="/tag/metadata">Metadata Tag</a>""",
        ),
    ],
)
def test_clear_html_structure(test_id, input_html, expected_output):
    """Test HTML structure cleaning functionality."""
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
@pytest.mark.parametrize(
    "test_id, input_html, expected_output",
    [
        # Original test cases
        (
            "removes_attributes",
            '<div class="test"><p style="color: red;">Hello, world!</p></div>',
            "<div><p>Hello, world!</p></div>",
        ),
        (
            "nested_tags",
            '<div class="test"><p style="color: red;">conserving O<sub class="calibre9">'
            '<small class="calibre10"><span class="calibre10"><span class="calibre2">2</span>'
            "</span></small></sub>,</p></div>",
            "<div><p>conserving O<sub><small><span><span>2</span></span></small></sub>,</p></div>",
        ),
        # Additional test cases
        (
            "preserve_id_attribute",
            '<div class="container" id="main"><p style="color: red;" id="para1">Text</p></div>',
            '<div id="main"><p id="para1">Text</p></div>',
        ),
        (
            "preserve_href_attribute",
            '<a href="https://example.com" class="link" target="_blank">Link</a>',
            '<a href="https://example.com" target="_blank">Link</a>',
        ),
        (
            "preserve_img_attributes",
            '<img src="image.jpg" class="image" alt="Test image" width="300" height="200">',
            '<img src="image.jpg" alt="Test image" width="300" height="200">',
        ),
    ],
)
def test_clear_html_attributes(test_id, input_html, expected_output):
    """Test HTML attribute handling."""
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
@pytest.mark.parametrize(
    "test_id, input_html, expected_output",
    [
        # Original test cases
        (
            "removes_consecutive_br_tags",
            "<div>Line 1<br><br>Line 2</div>",
            "<div>Line 1<br>Line 2</div>",
        ),
        (
            "removes_consecutive_br_tags_with_whitespace",
            "<div>Line 1<br>  \n  <br>Line 2</div>",
            "<div>Line 1<br> Line 2</div>",
        ),
        (
            "removes_multiple_br_tags_in_p",
            '<p><span id="word-42">vremena</span>. <br> <br> <br> <br> <br> <br> <br> <br></p>',
            '<p><span id="word-42">vremena</span>. <br> </p>',
        ),
        (
            "removes_div_with_only_br_tags",
            "<div><div><br><br></div><p>Content</p></div>",
            "<div><p>Content</p></div>",
        ),
        (
            "removes_div_with_br_and_whitespace",
            "<div><div>  <br>  \n  </div><p>Content</p></div>",
            "<div><p>Content</p></div>",
        ),
        (
            "removes_nested_div_with_only_br",
            "<div><div> <br> <div> <br> </div> <br> </div><p>Content</p></div>",
            "<div><p>Content</p></div>",
        ),
        (
            "keeps_div_with_content_and_br",
            "<div><div>Text<br></div><p>Content</p></div>",
            "<div><div>Text<br></div><p>Content</p></div>",
        ),
        # Additional test cases
        (
            "br_with_tail_content",
            "<div><br>Some text after br</div>",
            "<div><br>Some text after br</div>",
        ),
        (
            "multiple_br_with_content_between",
            "<div>Line 1<br>Between content<br>Line 2</div>",
            "<div>Line 1<br>Between content<br>Line 2</div>",
        ),
    ],
)
def test_clear_html_br_handling(test_id, input_html, expected_output):
    """Test handling of <br> tags."""
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
@pytest.mark.parametrize(
    "test_id, input_html, expected_output",
    [
        # Original test cases
        ("handles_empty_input", "", ""),
        (
            "removes_empty_p_tags",
            "<div><p>Content</p><p>  </p><p>\n\t</p></div>",
            "<div><p>Content</p></div>",
        ),
        (
            "removes_nested_div_with_only_spaces",
            "<div><p>Content <br>\n<div><p>\n</p></div><br/> </p></div>",
            "<div><p>Content <br> </p><br> </div>",
        ),
        # Additional test cases
        ("empty_div_tags", "<div><div></div><p>Content</p></div>", "<div><p>Content</p></div>"),
        (
            "nested_empty_elements",
            "<div><span><em></em></span><p>Content</p></div>",
            "<div><p>Content</p></div>",
        ),
        (
            "keep_empty_img_tag",
            "<div><img src='image.jpg'><p>Content</p></div>",
            """<div><img src="image.jpg"><p>Content</p></div>""",
        ),
        ("keep_empty_br_tag", "<div><br><p>Content</p></div>", "<div><br><p>Content</p></div>"),
        ("keep_empty_hr_tag", "<div><hr><p>Content</p></div>", "<div><hr><p>Content</p></div>"),
        (
            "keep_img",
            '<div><img id="Image1graphic" src="../Images/image001.jpg"></div>',
            '<div><img id="Image1graphic" src="../Images/image001.jpg"></div>',
        ),
    ],
)
def test_clear_html_empty_elements(test_id, input_html, expected_output):
    """Test handling of empty elements."""
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
@pytest.mark.parametrize(
    "test_id, input_html, expected_output, tags_with_classes",
    [
        (
            "add_default_classes_to_h1",
            "<div><h1>Heading 1</h1></div>",
            '<div><h1 class="display-4 fw-semibold text-primary mb-4">Heading 1</h1></div>',
            None,
        ),
        (
            "add_default_classes_to_h2",
            "<div><h2>Heading 2</h2></div>",
            '<div><h2 class="display-5 fw-semibold text-secondary mb-3">Heading 2</h2></div>',
            None,
        ),
        (
            "add_custom_classes_to_h1",
            "<div><h1>Heading 1</h1></div>",
            '<div><h1 class="custom-h1">Heading 1</h1></div>',
            {"h1": "custom-h1"},
        ),
        (
            "add_multiple_custom_classes",
            "<div><h1>Heading 1</h1><h2>Heading 2</h2></div>",
            '<div><h1 class="h1-class">Heading 1</h1><h2 class="h2-class">Heading 2</h2></div>',
            {"h1": "h1-class", "h2": "h2-class"},
        ),
        (
            "add_classes_to_p",
            "<div><p>Paragraph</p></div>",
            '<div><p class="p-class">Paragraph</p></div>',
            {"p": "p-class"},
        ),
    ],
)
def test_clear_html_add_classes(test_id, input_html, expected_output, tags_with_classes):
    """Test adding classes to tags."""
    result = clear_html(input_html, tags_with_classes=tags_with_classes)

    # Parse both expected and actual HTML for comparison
    # This helps handle whitespace differences and attribute order
    result_soup = BeautifulSoup(result, "html.parser")
    expected_soup = BeautifulSoup(expected_output, "html.parser")

    # Check if the structure and attributes match
    for tag_name in ["h1", "h2", "p"]:
        result_tags = result_soup.find_all(tag_name)
        expected_tags = expected_soup.find_all(tag_name)

        assert len(result_tags) == len(expected_tags), f"Number of {tag_name} tags doesn't match"

        for result_tag, expected_tag in zip(result_tags, expected_tags):
            # Check class attribute
            result_class = result_tag.get("class", [])
            expected_class = expected_tag.get("class", [])
            assert set(result_class) == set(expected_class), (
                f"Classes for {tag_name} don't match: {result_class} vs {expected_class}"
            )


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
@pytest.mark.parametrize(
    "test_id, input_html, ids_to_keep, expected_tag_preserved",
    [
        (
            "keep_custom_tag_with_id",
            '<div><custom-tag id="keep-me">Content</custom-tag></div>',
            ["keep-me"],
            True,
        ),
        (
            "ignore_custom_tag_without_id",
            "<div><custom-tag>Content</custom-tag></div>",
            ["keep-me"],
            False,
        ),
        (
            "keep_empty_div_with_id",
            '<div><div id="keep-empty"></div><p>Content</p></div>',
            ["keep-empty"],
            True,
        ),
    ],
)
def test_clear_html_keep_ids(test_id, input_html, ids_to_keep, expected_tag_preserved):
    """Test preserving elements with specific IDs."""
    result = clear_html(input_html, ids_to_keep=ids_to_keep)
    soup = BeautifulSoup(result, "html.parser")

    # Check if elements with the specific ID are preserved
    for id_to_keep in ids_to_keep:
        element = soup.find(id=id_to_keep)
        assert (element is not None) == expected_tag_preserved, (
            f"Element with ID '{id_to_keep}' should be {'preserved' if expected_tag_preserved else 'removed'}"
        )


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
@pytest.mark.parametrize(
    "test_id, input_html, expected_output",
    [
        # Original test cases
        (
            "removes_comments",
            "<div><!-- This is a comment -->Content<!-- Another comment --></div>",
            "<div>Content</div>",
        ),
        # Additional test cases
        (
            "remove_comments_in_tags",
            "<div><p>Before<!-- Comment -->After</p></div>",
            "<div><p>BeforeAfter</p></div>",
        ),
        (
            "handle_malformed_comment",
            "<div><!-- Unfinished comment <p>Content</p></div>",
            "<div>&lt;!-- Unfinished comment <p>Content</p></div>",
        ),
    ],
)
def test_clear_html_comments(test_id, input_html, expected_output):
    """Test handling of HTML comments."""
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
@pytest.mark.parametrize(
    "test_id, input_html, expected_output",
    [
        (
            "normalize_newlines",
            "<div>Line 1\nLine 2\r\nLine 3</div>",
            "<div>Line 1 Line 2 Line 3</div>",
        ),
        (
            "collapse_whitespace",
            "<div>  Multiple    spaces  </div>",
            "<div> Multiple spaces </div>",
        ),
        ("trim_whitespace", "  <div>Content</div>  ", "<div>Content</div>"),
    ],
)
def test_clear_html_whitespace(test_id, input_html, expected_output):
    """Test whitespace handling."""
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clear_html_error_handling():
    """Test that clear_html handles errors gracefully and returns original input."""
    # Malformed HTML that might cause parsing errors
    input_html = "<small>begin<div><unclosed_tag><span>end</small><p>paragraph</p>"
    # Expect the function to return the original input when encountering errors
    assert (
        clear_html(input_html) == "<small>begin<div><span>end<p>paragraph</p></span></div></small>"
    )


# Test complex case
@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clear_html_complex_case():
    """Test a complex case with multiple cleaning rules."""
    input_html = """
    <div>
        <!-- Header comment -->
        <p>  </p>
        <h1>Title<!-- comment inside --></h1>
        <p>Content</p>
        <br><br><br>
        <!-- Another comment -->
        <div><br>  <br></div>
        <p>\t \n</p>
        <div>Text<br><br>More text</div>
    </div>
    """
    expected_output = """
    <div>

        <h1 class="display-4 fw-semibold text-primary mb-4">Title</h1>
        <p>Content</p>
        <br>


        <div>Text<br>More text</div>
    </div>
    """

    # Compare without whitespace
    cleaned = "".join(clear_html(input_html).split())
    expected = "".join(expected_output.split())

    assert cleaned == expected


# Custom tags and edge cases
@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
@pytest.mark.parametrize(
    "test_id, input_html, expected_pattern, custom_allowed_tags",
    [
        (
            "default_allowed_tags",
            "<div><custom-tag>Content</custom-tag></div>",
            "<div>Content</div>",
            None,
        ),
        (
            "custom_allowed_tags",
            "<div><custom-tag>Content</custom-tag></div>",
            "<div><custom-tag>Content</custom-tag></div>",
            ALLOWED_TAGS + ("custom-tag",),
        ),
        (
            "nested_custom_tags",
            "<div><custom-outer><custom-inner>Content</custom-inner></custom-outer></div>",
            "<div>Content</div>",
            None,
        ),
    ],
)
def test_clear_html_custom_tags(test_id, input_html, expected_pattern, custom_allowed_tags):
    """Test handling of custom tags with configurable allowed tags."""
    from lexiflux.ebook.clear_html import ALLOWED_TAGS

    result = clear_html(input_html, allowed_tags=custom_allowed_tags or ALLOWED_TAGS)

    # For simplicity, compare without whitespace
    result_no_space = "".join(result.split())
    expected_no_space = "".join(expected_pattern.split())

    assert result_no_space == expected_no_space


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clear_html_whitelist_nested_unknown_tags():
    input_html = """<custom-container>
                      <p>This paragraph is allowed</p>
                      <unknown-tag>
                        <p>This paragraph inside unknown tag should be kept</p>
                        <another-unknown>This text should remain</another-unknown>
                      </unknown-tag>
                    </custom-container>"""

    # Expected output - unknown tags are removed, but content is kept
    expected_output = """
                      <p>This paragraph is allowed</p>

                        <p>This paragraph inside unknown tag should be kept</p>
                        This text should remain

                    """

    # Strip whitespace for comparison
    cleaned = clear_html(input_html).replace(" ", "")
    expected = expected_output.replace(" ", "")
    # Compare without whitespace
    expected = "".join(expected.split())
    assert cleaned == expected


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clear_html_adds_classes_to_tags():
    input_html = """
    <div>
        <h1>This is a heading 1</h1>
        <h2>This is a heading 2</h2>
        <h3>This is a heading 3</h3>
        <h4>This is a heading 4</h4>
        <h5>This is a heading 5</h5>
        <p>This is a paragraph</p>
    </div>
    """

    # Custom tags with classes
    tags_with_classes = {"h1": "custom-h1", "h2": "custom-h2 secondary", "p": "paragraph-class"}

    cleaned_html = clear_html(input_html, tags_with_classes=tags_with_classes)
    soup = BeautifulSoup(cleaned_html, "html.parser")

    # Check headings have the correct classes
    h1 = soup.find("h1")
    assert h1 is not None
    assert "class" in h1.attrs, "h1 should have class attribute"
    assert h1["class"] == ["custom-h1"], "h1 should have custom-h1 class"

    h2 = soup.find("h2")
    assert h2 is not None
    assert "class" in h2.attrs, "h2 should have class attribute"
    assert set(h2["class"]) == {"custom-h2", "secondary"}, "h2 should have both classes"

    # Check paragraph also gets classes when specified
    p = soup.find("p")
    assert p is not None
    assert "class" in p.attrs, "p should have class attribute"
    assert p["class"] == ["paragraph-class"], "p should have paragraph-class"

    # Check h3 do not have classes (since not in custom tags_with_classes)
    h3 = soup.find("h3")
    assert h3 is not None
    assert "class" not in h3.attrs, "h3 should not have class attribute"


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clear_html_preserves_all_attributes_except_style_and_class():
    input_html = """
    <div class="container" style="margin: 20px;" id="main" data-test="value" role="main">
        <a href="https://example.com" class="link" target="_blank" rel="noopener" aria-label="Example">Link</a>
        <img src="image.jpg" class="image" style="width: 100%;" alt="Test image" loading="lazy" width="300" height="200">
    </div>
    """

    cleaned_html = clear_html(input_html)
    soup = BeautifulSoup(cleaned_html, "html.parser")

    # Check div attributes
    div = soup.find("div")
    assert div is not None
    assert "class" not in div.attrs, "class should be removed"
    assert "style" not in div.attrs, "style should be removed"
    assert "id" in div.attrs, "id should be preserved"
    assert "data-test" in div.attrs, "data-test should be preserved"
    assert "role" in div.attrs, "role should be preserved"

    # Check a attributes
    a = soup.find("a")
    assert a is not None
    assert "class" not in a.attrs, "class should be removed"
    assert "href" in a.attrs, "href should be preserved"
    assert "target" in a.attrs, "target should be preserved"
    assert "rel" in a.attrs, "rel should be preserved"
    assert "aria-label" in a.attrs, "aria-label should be preserved"

    # Check img attributes
    img = soup.find("img")
    assert img is not None
    assert "class" not in img.attrs, "class should be removed"
    assert "style" not in img.attrs, "style should be removed"
    assert "src" in img.attrs, "src should be preserved"
    assert "alt" in img.attrs, "alt should be preserved"
    assert "loading" in img.attrs, "loading should be preserved"
    assert "width" in img.attrs, "width should be preserved"
    assert "height" in img.attrs, "height should be preserved"


def normalize_whitespace(html_string):
    """Normalize whitespace in HTML strings for comparison."""
    # Replace all whitespace sequences (including newlines) with a single space
    normalized = re.sub(r"\s+", " ", html_string)
    # Trim leading/trailing whitespace
    return normalized.strip()


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML - Complex Edge Cases")
class TestClearHtmlComplexEdgeCases:
    """Tests for complex edge cases in the clear_html function."""

    @pytest.mark.parametrize(
        "test_id, input_html, expected_output",
        [
            (
                "deeply_nested_structure_with_mixed_valid_invalid_tags",
                """
                    <section>
                        <article>
                            <custom-section>
                                <header>
                                    <h1>Title</h1>
                                    <nav>
                                        <ul>
                                            <li>Item 1</li>
                                            <li>Item 2</li>
                                        </ul>
                                    </nav>
                                </header>
                                <div>
                                    <p>This is a paragraph</p>
                                    <unknown-tag>Should be preserved <strong>but unwrapped</strong></unknown-tag>
                                </div>
                                <footer>Footer content</footer>
                            </custom-section>
                        </article>
                    </section>
                    """,
                """
                                <h1 class="display-4 fw-semibold text-primary mb-4">Title</h1>
    
                                    <ul>
                                        <li>Item 1</li>
                                        <li>Item 2</li>
                                    </ul>
    
                                <div>
                                    <p>This is a paragraph</p>
                                    Should be preserved <strong>but unwrapped</strong>
                                </div>
                                Footer content
                    """,
            ),
            (
                "fragment_with_text_before_and_after_elements",
                """
                    Text before elements
                    <div>Content inside div</div>
                    Text between elements
                    <p>Content inside paragraph</p>
                    Text after elements
                    """,
                """
                    <p>Text before elements </p><div>Content inside div</div>
                    Text between elements
                    <p>Content inside paragraph</p>
                    Text after elements
                    """,
            ),
        ],
    )
    def test_clear_html_complex_nested_structures(self, test_id, input_html, expected_output):
        """Test handling of complex nested structures with text nodes."""
        # Clean HTML and normalize whitespace for comparison
        cleaned = normalize_whitespace(clear_html(input_html))
        expected = normalize_whitespace(expected_output)

        assert cleaned == expected

    @pytest.mark.parametrize(
        "test_id, input_html, expected_output",
        [
            (
                "malformed_unclosed_tags",
                """
                    <div>
                        <p>Paragraph with <strong>bold text
                        <em>and italics</p>
                        <p>Another paragraph</p>
                    </div>
                    """,
                """
                    <div>
                        <p>Paragraph with <strong>bold text
                        <em>and italics</em></strong></p>
                        <p>Another paragraph</p>
                    </div>
                    """,
            ),
            (
                "malformed_improperly_nested",
                """
                    <div>
                        <p>Text with <b>bold and <i>italic</b> overlapping</i> tags</p>
                    </div>
                    """,
                """
                    <div>
                        <p>Text with <b>bold and <i>italic</i></b> overlapping tags</p>
                    </div>
                    """,
            ),
        ],
    )
    def test_clear_html_malformed_html(self, test_id, input_html, expected_output):
        """Test handling of malformed HTML with unclosed or improperly nested tags."""
        result = clear_html(input_html)

        # Parse both to compare DOM structure rather than exact string matching
        result_soup = BeautifulSoup(result, "html.parser")
        expected_soup = BeautifulSoup(expected_output, "html.parser")

        # Compare normalized serialized versions
        assert normalize_whitespace(str(result_soup)) == normalize_whitespace(str(expected_soup))

    @pytest.mark.parametrize(
        "test_id, input_html, expected_output",
        [
            (
                "html_entities",
                """
                    <div>
                        <p>Entity: &lt;div&gt; &amp; &quot;quotes&quot; &apos;apostrophes&apos;</p>
                        <p>Numeric entities: &#60;div&#62; &#38; &#34;quotes&#34;</p>
                        <p>Special chars: &copy; &reg; &euro; &pound;</p>
                    </div>
                    """,
                """
                    <div>
                        <p>Entity: &lt;div&gt; &amp; "quotes" 'apostrophes'</p>
                        <p>Numeric entities: &lt;div&gt; &amp; "quotes"</p>
                        <p>Special chars: © ® € £</p>
                    </div>
                    """,
            ),
            (
                "cdata_sections",
                """
                    <div>
                        <![CDATA[This is CDATA content with <tags> that shouldn't be parsed]]>
                        Normal text
                        <![CDATA[This is another CDATA content with <tags> that shouldn't be parsed]]>
                        More text
                    </div>
                    """,
                """
                    <div>
                        Normal text
                        More text
                    </div>
                    """,
            ),
        ],
    )
    def test_clear_html_entities_and_cdata(self, test_id, input_html, expected_output):
        """Test handling of HTML entities and CDATA sections."""
        # Clean HTML
        cleaned = clear_html(input_html)

        # Parse both as BeautifulSoup objects to normalize entity handling
        result_soup = BeautifulSoup(cleaned, "html.parser")
        expected_soup = BeautifulSoup(expected_output, "html.parser")

        # Compare normalized versions
        assert normalize_whitespace(str(result_soup)) == normalize_whitespace(str(expected_soup))

    @pytest.mark.parametrize(
        "test_id, input_html, expected_output",
        [
            (
                "empty_div_at_end_with_tail_text",
                """
                    <div>
                        <p>Content</p>
                        <div></div>Text after empty div
                    </div>
                    """,
                """
                    <div>
                        <p>Content</p>
                        Text after empty div
                    </div>
                    """,
            ),
            (
                "nested_empty_elements_with_tail_text",
                """
                    <div>
                        <span><em></em>Text after empty em</span>
                        <p>Content</p>
                    </div>
                    """,
                """
                    <div>
                        <span>Text after empty em</span>
                        <p>Content</p>
                    </div>
                    """,
            ),
            (
                "nested_empty_elements_with_self_closing_tags",
                """
                        <div>
                            <span><em/>Text after empty self closing em</span>
                            <p>Content</p>
                        </div>
                        """,
                """
                        <div>
                            <span>Text after empty self closing em</span>
                            <p>Content</p>
                        </div>
                        """,
            ),
            (
                "br_with_important_tail",
                """
                    <div>
                        <p>Line 1<br><br><!-- This should be removed --><br>Important text after multiple br tags</p>
                    </div>
                    """,
                """
                    <div>
                        <p>Line 1<br>Important text after multiple br tags</p>
                    </div>
                    """,
            ),
        ],
    )
    def test_clear_html_empty_elements_with_tail_text(self, test_id, input_html, expected_output):
        """Test handling of empty elements with important tail text."""
        cleaned = " ".join(clear_html(input_html).split())
        expected = " ".join(expected_output.split())

        assert cleaned == expected

    @pytest.mark.parametrize(
        "test_id, input_html, ids_to_keep, expected_output",
        [
            (
                "preserve_attribute_precedence_with_ids",
                """
                    <custom-container id="custom-id">
                        <custom-header id="header-id">This header should be kept</custom-header>
                        <custom-content>This should be unwrapped</custom-content>
                        <div id="not-in-list"></div>
                        <div id="custom-id"></div>
                    </custom-container>
                    """,
                ["custom-id", "header-id"],
                """
                    <custom-container id="custom-id">
                        <custom-header id="header-id">This header should be kept</custom-header>
                        This should be unwrapped
                        <div id="custom-id"></div>
                    </custom-container>
                    """,
            ),
            (
                "preserve_ids_with_namespaced_elements",
                """
                    <ns:custom-element id="ns-id" xmlns:ns="http://example.org/ns">
                        <ns:child id="child-id">Namespaced content</ns:child>
                    </ns:custom-element>
                    """,
                ["ns-id", "child-id"],
                """
                    <ns:custom-element id="ns-id" xmlns:ns="http://example.org/ns">
                        <ns:child id="child-id">Namespaced content</ns:child>
                    </ns:custom-element>
                    """,
            ),
        ],
    )
    def test_clear_html_ids_to_keep_precedence(
        self, test_id, input_html, ids_to_keep, expected_output
    ):
        """Test that IDs to keep take precedence over tag filtering."""
        result = clear_html(input_html, ids_to_keep=ids_to_keep)

        # Parse both to normalize for comparison
        result_soup = BeautifulSoup(result, "html.parser")
        expected_soup = BeautifulSoup(expected_output, "html.parser")

        # Check IDs are preserved
        for id_value in ids_to_keep:
            assert result_soup.find(id=id_value) is not None, (
                f"Element with id={id_value} should be preserved"
            )

        # Compare normalized structures
        assert normalize_whitespace(str(result_soup)) == normalize_whitespace(str(expected_soup))

    @pytest.mark.parametrize(
        "test_id, input_html, expected_output",
        [
            (
                "svg_and_math_content",
                """
                    <div>
                        <svg width="100" height="100">
                            <circle cx="50" cy="50" r="40" stroke="black" fill="red" />
                        </svg>
                        <math>
                            <mi>x</mi><mo>+</mo><mn>1</mn><mo>=</mo><mn>0</mn>
                        </math>
                        <p>Regular content</p>
                    </div>
                    """,
                """
                    <div>
    
                            x+1=0
    
                        <p>Regular content</p>
                    </div>
                    """,
            ),
            (
                "xml_processing_instructions",
                """
                    <?xml version="1.0" encoding="UTF-8"?>
                    <?xml-stylesheet type="text/css" href="style.css"?>
                    <!DOCTYPE html>
                    <div>
                        <p>Content after processing instructions</p>
                    </div>
                    """,
                """
    
    
    
                    <div>
                        <p>Content after processing instructions</p>
                    </div>
                    """,
            ),
        ],
    )
    def test_clear_html_xml_and_special_content(self, test_id, input_html, expected_output):
        """Test handling of SVG, MathML content and XML processing instructions."""
        # Focus on structure rather than whitespace
        cleaned = " ".join(clear_html(input_html).split())
        expected = " ".join(expected_output.split())

        # Parse both for DOM comparison
        result_soup = BeautifulSoup(cleaned, "html.parser")
        expected_soup = BeautifulSoup(expected, "html.parser")

        # Compare normalized versions
        assert str(result_soup) == str(expected_soup)

    @pytest.mark.parametrize(
        "test_id, input_html, keep_empty_tags, expected_output",
        [
            (
                "custom_keep_empty_tags",
                """
                    <div>
                        <span></span>
                        <custom-empty></custom-empty>
                        <p>Content</p>
                    </div>
                    """,
                KEEP_EMPTY_TAGS + ("custom-empty",),
                """
                    <div>
                        <custom-empty></custom-empty>
                        <p>Content</p>
                    </div>
                    """,
            ),
            (
                "override_keep_empty_tags",
                """
                    <div>
                        <img src="image.jpg">
                        <br>
                        <p>Content</p>
                    </div>
                    """,
                ("img",),  # Only keep img, not br
                """
                    <div>
                        <img src="image.jpg">
                        <p>Content</p>
                    </div>
                    """,
            ),
        ],
    )
    def test_clear_html_custom_keep_empty_tags(
        self, test_id, input_html, keep_empty_tags, expected_output
    ):
        """Test customization of which empty tags to keep."""
        result = clear_html(input_html, keep_empty_tags=keep_empty_tags)

        # Parse both for comparison
        result_soup = BeautifulSoup(result, "html.parser")
        expected_soup = BeautifulSoup(expected_output, "html.parser")

        # Compare normalized versions
        assert normalize_whitespace(str(result_soup)) == normalize_whitespace(str(expected_soup))

    @pytest.mark.parametrize(
        "test_id, input_html, tags_to_remove, expected_output",
        [
            (
                "custom_tags_to_remove_with_content",
                """
                    <div>
                        <script>alert('Test');</script>
                        <remove-me>This should be removed</remove-me>
                        <p>This should stay</p>
                    </div>
                    """,
                REMOVE_WITH_CONTENT + ("remove-me",),
                """
                    <div>
                        <p>This should stay</p>
                    </div>
                    """,
            ),
            (
                "override_tags_to_remove",
                """
                    <div>
                        <script>alert('Test');</script>
                        <style>.test { color: red; }</style>
                        <p>Content</p>
                    </div>
                    """,
                ("style",),  # Remove with content style, keep content of script
                """
                    <div>
                        alert('Test');
                        <p>Content</p>
                    </div>
                    """,
            ),
        ],
    )
    def test_clear_html_custom_tags_to_remove_with_content(
        self, test_id, input_html, tags_to_remove, expected_output
    ):
        """Test customization of which tags to remove with their content."""
        result = clear_html(input_html, tags_to_remove_with_content=tags_to_remove)

        # Parse both for comparison
        result_soup = BeautifulSoup(result, "html.parser")
        expected_soup = BeautifulSoup(expected_output, "html.parser")

        # Compare normalized versions
        assert normalize_whitespace(str(result_soup)) == normalize_whitespace(str(expected_soup))

    @pytest.mark.parametrize(
        "test_id, input_html, expected_output",
        [
            (
                "mixed_unicode_and_special_chars",
                """
                    <div>
                        <p>Unicode: ♥ ☺ ★ 你好 привет</p>
                        <p>Mixed with HTML: <span>♥</span> &hearts; <b>★</b></p>
                        <p>Special spaces: no-break space [&#160;] em space [&#8195;]</p>
                        <p>Control chars: [&#x200B;] zero-width space</p>
                    </div>
                    """,
                """
                    <div>
                        <p>Unicode: ♥ ☺ ★ 你好 привет</p>
                        <p>Mixed with HTML: <span>♥</span> ♥ <b>★</b></p>
                        <p>Special spaces: no-break space [ ] em space [ ]</p>
                        <p>Control chars: [&#x200B;] zero-width space</p>
                    </div>
                    """,
            ),
            (
                "emoji_and_surrogate_pairs",
                """
                    <div>
                        <p>Emoji: 🚀 🌍 👨‍👩‍👧‍👦 👾</p>
                        <p>Flags: 🇺🇸 🏳️‍🌈 🏴‍☠️</p>
                    </div>
                    """,
                """
                    <div>
                        <p>Emoji: 🚀 🌍 👨‍👩‍👧‍👦 👾</p>
                        <p>Flags: 🇺🇸 🏳️‍🌈 🏴‍☠️</p>
                    </div>
                    """,
            ),
        ],
    )
    def test_clear_html_unicode_and_special_characters(self, test_id, input_html, expected_output):
        """Test handling of Unicode characters, emoji, and special whitespace."""
        result = clear_html(input_html)

        # Parse both for comparison while preserving Unicode
        result_soup = BeautifulSoup(result, "html.parser")
        expected_soup = BeautifulSoup(expected_output, "html.parser")

        # Compare normalized versions
        assert normalize_whitespace(str(result_soup)) == normalize_whitespace(str(expected_soup))

    @pytest.mark.parametrize(
        "test_id, input_html, expected_output",
        [
            (
                "extreme_tag_nesting_depth",
                "<div>"
                + "<span>".join(["" for _ in range(100)])
                + "Deep content"
                + "</span>" * 100
                + "</div>",
                "<div>"
                + "<span>".join(["" for _ in range(100)])
                + "Deep content"
                + "</span>" * 100
                + "</div>",
            ),
            (
                "very_long_text_content",
                f"<p>{'Lorem ipsum ' * 1000}</p>",
                f"<p>{'Lorem ipsum ' * 1000}</p>",
            ),
            (
                "huge_number_of_siblings",
                "<div>" + "".join([f"<span>Item {i}</span>" for i in range(500)]) + "</div>",
                "<div>" + "".join([f"<span>Item {i}</span>" for i in range(500)]) + "</div>",
            ),
        ],
    )
    def test_clear_html_performance_edge_cases(self, test_id, input_html, expected_output):
        """Test handling of extreme cases that might affect performance."""
        # We just check that the function completes without error
        # and returns something reasonable for these extreme cases
        result = clear_html(input_html)
        assert len(result) > 0, "Result should not be empty"

        # For the extreme nesting case, verify that the deep content is preserved
        if test_id == "extreme_tag_nesting_depth":
            assert "Deep content" in result

        # For the very long text case, check that the content is preserved
        elif test_id == "very_long_text_content":
            assert "Lorem ipsum" in result
            assert len(result) > 1000

        # For the huge siblings case, verify that some siblings are preserved
        elif test_id == "huge_number_of_siblings":
            assert "Item 1" in result and "Item 499" in result

    @pytest.mark.parametrize(
        "test_id, input_html, expected_output",
        [
            (
                "edge_case_with_namespaced_attributes",
                """
                    <div xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:epub="http://www.idpf.org/2007/ops">
                        <p epub:type="bridgehead">Special paragraph</p>
                        <a xlink:href="chapter1.html">Link with namespace</a>
                    </div>
                    """,
                """
                    <div xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:epub="http://www.idpf.org/2007/ops">
                        <p epub:type="bridgehead">Special paragraph</p>
                        <a xlink:href="chapter1.html">Link with namespace</a>
                    </div>
                    """,
            ),
            (
                "edge_case_with_data_attributes",
                """
                    <div>
                        <p data-ref="123" data-custom="value">Paragraph with data attributes</p>
                        <span data-test="test" data-index="0">Span with data</span>
                    </div>
                    """,
                """
                    <div>
                        <p data-ref="123" data-custom="value">Paragraph with data attributes</p>
                        <span data-test="test" data-index="0">Span with data</span>
                    </div>
                    """,
            ),
        ],
    )
    def test_clear_html_special_attribute_handling(self, test_id, input_html, expected_output):
        """Test handling of namespaced and data-* attributes."""
        result = clear_html(input_html)

        # Parse both for comparison
        result_soup = BeautifulSoup(result, "html.parser")
        expected_soup = BeautifulSoup(expected_output, "html.parser")

        # Check that namespaced attributes are preserved
        if test_id == "edge_case_with_namespaced_attributes":
            assert "epub:type" in result
            assert "xlink:href" in result

        # Check that data attributes are preserved
        elif test_id == "edge_case_with_data_attributes":
            assert "data-ref" in result
            assert "data-custom" in result
            assert "data-test" in result
            assert "data-index" in result

        # Compare normalized versions
        assert normalize_whitespace(str(result_soup)) == normalize_whitespace(str(expected_soup))
