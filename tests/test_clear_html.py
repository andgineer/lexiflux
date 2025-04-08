import allure
from bs4 import BeautifulSoup

from lexiflux.ebook.clear_html import clear_html


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_head():
    input_html = "<html><head><title>Test</title></head><body><p>Hello, world!</p></body></html>"
    expected_output = "<p>Hello, world!</p>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_escape_unknown_tags():
    input_html = (
        '<header class=""><section class="header-top py-1">some header</section>in header</header>'
    )
    expected_output = "some headerin header"
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
def test_clean_html_nested_tags():
    input_html = '<div class="test"><p style="color: red;">conserving O<sub class="calibre9"><small class="calibre10"><span class="calibre10"><span class="calibre2">2</span></span></small></sub>,</p></div>'
    expected_output = (
        "<div><p>conserving O<sub><small><span><span>2</span></span></small></sub>,</p></div>"
    )
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_handles_empty_input():
    input_html = ""
    expected_output = ""
    assert clear_html(input_html) == expected_output


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


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_comments():
    input_html = "<div><!-- This is a comment -->Content<!-- Another comment --></div>"
    expected_output = "<div>Content</div>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_empty_p_tags():
    input_html = "<div><p>Content</p><p>  </p><p>\n\t</p></div>"
    expected_output = "<div><p>Content</p></div>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_consecutive_br_tags():
    input_html = "<div>Line 1<br><br>Line 2</div>"
    expected_output = "<div>Line 1<br>Line 2</div>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_consecutive_br_tags_with_whitespace():
    input_html = "<div>Line 1<br>  \n  <br>Line 2</div>"
    expected_output = "<div>Line 1<br> Line 2</div>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_multiple_br_tags_in_p():
    input_html = '<p><span class="word" id="word-42">vremena</span>. <br> <br> <br> <br> <br> <br> <br> <br></p>'
    expected_output = '<p><span id="word-42">vremena</span>. <br> </p>'
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_div_with_only_br_tags():
    input_html = "<div><div><br><br></div><p>Content</p></div>"
    expected_output = "<div><p>Content</p></div>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_div_with_br_and_whitespace():
    input_html = "<div><div>  <br>  \n  </div><p>Content</p></div>"
    expected_output = "<div><p>Content</p></div>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_nested_div_with_only_br():
    input_html = "<div><div> <br> <div> <br> </div> <br> </div><p>Content</p></div>"
    expected_output = "<div><p>Content</p></div>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_keeps_div_with_content_and_br():
    input_html = "<div><div>Text<br></div><p>Content</p></div>"
    expected_output = "<div><div>Text<br></div><p>Content</p></div>"
    assert clear_html(input_html) == expected_output


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_complex_case():
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

        <h1 class="display-4fw-semiboldtext-primarymb-4">Title</h1>
        <p>Content</p>
        <br>


        <div>Text<br>More text</div>
    </div>
    """

    # Compare without whitespace
    cleaned = "".join(clear_html(input_html).split())
    expected = "".join(expected_output.split())

    assert cleaned == expected


@allure.epic("Book import")
@allure.feature("EPUB: Clean HTML")
def test_clean_html_removes_nested_div_with_only_spaces():
    input_html = "<div><p>Content <br>\n<div><p>\n</p></div><br/> </p></div>"
    expected_output = "<div><p>Content <br> </p><br> </div>"
    assert clear_html(input_html) == expected_output
