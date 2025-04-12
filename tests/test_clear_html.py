import pytest
import allure
from bs4 import BeautifulSoup

from lexiflux.ebook.clear_html import clear_html, ALLOWED_TAGS


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
    ],
)
def test_clean_html_structure(test_id, input_html, expected_output):
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
def test_clean_html_attributes(test_id, input_html, expected_output):
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
def test_clean_html_br_handling(test_id, input_html, expected_output):
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
def test_clean_html_empty_elements(test_id, input_html, expected_output):
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
def test_clean_html_add_classes(test_id, input_html, expected_output, tags_with_classes):
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
def test_clean_html_keep_ids(test_id, input_html, ids_to_keep, expected_tag_preserved):
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
def test_clean_html_comments(test_id, input_html, expected_output):
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
def test_clean_html_whitespace(test_id, input_html, expected_output):
    """Test whitespace handling."""
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_error_handling():
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
def test_clean_html_complex_case():
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
def test_clean_html_custom_tags(test_id, input_html, expected_pattern, custom_allowed_tags):
    """Test handling of custom tags with configurable allowed tags."""
    from lexiflux.ebook.clear_html import ALLOWED_TAGS

    result = clear_html(input_html, allowed_tags=custom_allowed_tags or ALLOWED_TAGS)

    # For simplicity, compare without whitespace
    result_no_space = "".join(result.split())
    expected_no_space = "".join(expected_pattern.split())

    assert result_no_space == expected_no_space


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_whitelist_nested_unknown_tags():
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
def test_clean_html_adds_classes_to_tags():
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
def test_clean_html_preserves_all_attributes_except_style_and_class():
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
