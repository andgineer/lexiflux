import pytest
from lexiflux.language.html_tags_cleaner import clear_html_tags


def test_clear_html_tags_basic():
    html = "<p>This is a <strong>test</strong>.</p>"
    assert clear_html_tags(html) == "This is a test."


def test_clear_html_tags_nested():
    html = "<div><p>Nested <span>tags</span> here</p></div>"
    assert clear_html_tags(html) == "Nested tags here"


def test_clear_html_tags_with_attributes():
    html = '<a href="https://example.com" class="link">Link</a>'
    assert clear_html_tags(html) == "Link"


def test_clear_html_tags_self_closing():
    html = "An image: <img src='test.jpg' alt='Test'/> and a break <br>"
    assert clear_html_tags(html) == "An image:  and a break "


def test_clear_html_tags_invalid_tags():
    html = "<p>Valid tag</p> <inv@lid>Invalid tag</inv@#lid>"
    assert clear_html_tags(html) == "Valid tag <inv@lid>Invalid tag</inv@#lid>"



def test_clear_html_tags_unpaired_invalid_tags():
    html = "<p>Valid tag</p> Invalid tag</inv@#lid>"
    assert clear_html_tags(html) == "Valid tag Invalid tag</inv@#lid>"


def test_clear_html_tags_mixed_valid_invalid():
    html = "<div>Valid <str@ng>Invalid <i>Mixed</i></str@ng></div>"
    assert clear_html_tags(html) == "Valid <str@ng>Invalid Mixed</str@ng>"


def test_clear_html_tags_empty_input():
    assert clear_html_tags("") == ""


def test_clear_html_tags_no_tags():
    text = "This is plain text without any tags."
    assert clear_html_tags(text) == text


def test_clear_html_tags_only_invalid_tags():
    html = "<str@ng>This should remain</str@ng> text"
    assert clear_html_tags(html) == html


def test_clear_html_tags_with_comments():
    html = "Before<!-- This is a comment -->After"
    assert clear_html_tags(html) == "BeforeAfter"


def test_clear_html_tags_script_and_style():
    html = "<script>var x = 5;</script><style>.cls { color: red; }</style>Content"
    assert clear_html_tags(html) == "Content"


def test_clear_html_tags_entities():
    html = "<p>This &amp; that &#38; those</p>"
    assert clear_html_tags(html) == "This & that & those"
