import pytest
from lexiflux.language.html_tags_cleaner import parse_tags, clear_html_tags


def test_html_tags_cleaner_basic():
    html = "<p>This is a <strong>test</strong>.</p>"
    plain_text, tag_slices, _ = parse_tags(html)
    assert plain_text == "This is a test."
    assert [html[start:end] for start, end in tag_slices] == ["<p>", "<strong>", "</strong>", "</p>"]


def test_html_tags_cleaner_nested():
    html = "<div><p>Nested <span>tags</span> here</p></div>"
    plain_text, tag_slices, _ = parse_tags(html)
    assert plain_text == "Nested tags here"
    assert [html[start:end] for start, end in tag_slices] == ["<div>", "<p>", "<span>", "</span>", "</p>", "</div>"]



def test_html_tags_cleaner_with_attributes():
    html = '<a href="https://example.com" class="link">Link</a>'
    plain_text, tag_slices, _ = parse_tags(html)
    assert plain_text == "Link"
    assert [html[start:end] for start, end in tag_slices] == ['<a href="https://example.com" class="link">', "</a>"]


def test_html_tags_cleaner_self_closing():
    html = "An image: <img src='test.jpg' alt='Test'/> and a break <br>"
    plain_text, tag_slices, _ = parse_tags(html)
    assert plain_text == "An image:  and a break "
    assert [html[start:end] for start, end in tag_slices] == ["<img src='test.jpg' alt='Test'/>", "<br>"]


def test_html_tags_cleaner_invalid_tags():
    html = "<p>Valid tag</p> <inv@lid>Invalid tag</inv@#lid>"
    plain_text, tag_slices, _ = parse_tags(html)
    assert plain_text == "Valid tag <inv@lid>Invalid tag</inv@#lid>"
    assert [html[start:end] for start, end in tag_slices] == ["<p>", "</p>"]


def test_html_tags_cleaner_script_and_style():
    html = "<script>var x = 5;</script><style>.cls { color: red; }</style>Content"
    plain_text, tag_slices, _ = parse_tags(html)
    assert plain_text == "Content"
    assert [html[start:end] for start, end in tag_slices] == [
        "<script>", "var x = 5;", "</script>", "<style>", ".cls { color: red; }", "</style>"
    ]


def test_html_tags_cleaner_entities():
    html = "<p>This &amp; that &#38; those</p>"
    plain_text, tag_slices, _ = parse_tags(html)
    assert plain_text == "This & that & those"
    assert [html[start:end] for start, end in tag_slices] == ["<p>", "</p>"]


def test_html_tags_cleaner_escaped_inside_word():
    html_str = "1 <br/> <br/> <br/> <br/> ALICE&#x27;S ADVENTURES IN <br/>"
    plain_text, tag_slices, _ = parse_tags(html_str)
    assert plain_text == "1     ALICE'S ADVENTURES IN "
    assert [html_str[start:end] for start, end in tag_slices] == ["<br/>", "<br/>", "<br/>", "<br/>", "<br/>"]


def test_html_tags_cleaner_tags_empty_input():
    assert clear_html_tags("") == ""


def test_html_tags_cleaner_no_tags():
    text = "This is plain text without any tags."
    assert clear_html_tags(text) == text


def test_html_tags_cleaner_only_invalid_tags():
    html = "<str@ng>This should remain</str@ng> text"
    assert clear_html_tags(html) == html


def test_html_tags_cleaner_with_comments():
    html_str = "Before<!-- This is a comment -->After"
    plain_text, tag_slices, _ = parse_tags(html_str)
    assert plain_text == "BeforeAfter"
    assert [html_str[start:end] for start, end in tag_slices] == ["<!-- This is a comment -->"]


def test_html_tags_cleaner_with_doctype():
    html_str = "<!DOCTYPE html><html><body>Content</body></html>"
    plain_text, tag_slices, _ = parse_tags(html_str)
    assert plain_text == "Content"
    assert [html_str[start:end] for start, end in tag_slices] == ["<!DOCTYPE html>", "<html>", "<body>", "</body>", "</html>"]

def test_html_tags_cleaner_with_processing_instruction():
    html_str = "<?xml version='1.0'?><root>Content</root>"
    plain_text, tag_slices, _ = parse_tags(html_str)
    assert plain_text == "<root>Content</root>"
    assert [html_str[start:end] for start, end in tag_slices] == ["<?xml version='1.0'?>"]


def test_html_tags_cleaner_with_cdata():
    html_str = "<![CDATA[This is CDATA content]]>Regular content"
    plain_text, tag_slices, _ = parse_tags(html_str)
    assert plain_text == "Regular content"
    assert [html_str[start:end] for start, end in tag_slices] == ["<![CDATA[This is CDATA content]]>"]


def test_html_tags_cleaner_with_entity_and_charref():
    html_str = "Entity: &lt; CharRef: &#60;"
    plain_text, tag_slices, _ = parse_tags(html_str)
    assert plain_text == "Entity: < CharRef: <"
    assert tag_slices == []


def test_html_tags_cleaner_with_script_and_style():
    html_str = "<script>alert('Hello');</script><style>body { color: red; }</style>Visible content"
    plain_text, tag_slices, _ = parse_tags(html_str)
    assert plain_text == "Visible content"
    assert [html_str[start:end] for start, end in tag_slices] == [
        "<script>", "alert('Hello');", "</script>",
        "<style>", "body { color: red; }", "</style>"
    ]


def test_html_tags_cleaner_complex():
    html_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <style>body { font-size: 16px; }</style>
    </head>
    <body>
        <!-- Header comment -->
        <h1>Welcome</h1>
        <p>This is a &lt;test&gt; page with &#60;various&#62; elements.</p>
        <script>console.log("Hello");</script>
        <?php echo "Server-side code"; ?>
        <![CDATA[Some CDATA content]]>
        <invalid>This tag is invalid</invalid>
    </body>
    </html>
    """
    plain_text, tag_slices, _ = parse_tags(html_str)
    assert plain_text.strip() == (
        "Test Page\n        \n    \n    \n        \n        "
        "Welcome\n        This is a <test> page with <various> elements."
        "\n        \n        \n        \n        <invalid>This tag is invalid</invalid>"
    )
    assert [html_str[start:end] for start, end in tag_slices] == [
        '<!DOCTYPE html>', '<html>', '<head>', '<title>', '</title>', '<style>', 'body { font-size: 16px; }',
        '</style>', '</head>', '<body>', '<!-- Header comment -->', '<h1>', '</h1>', '<p>', '</p>', '<script>',
        'console.log("Hello");', '</script>', '<?php echo "Server-side code"; ?>', '<![CDATA[Some CDATA content]]>',
        '</body>', '</html>'
    ]
