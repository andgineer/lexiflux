from lexiflux.language.word_extractor import parse_words, HTMLWordExtractor


def get_content_by_indices(content, indices):
    return [content[start:end] for start, end in indices]


def test_word_extractor_simple_text():
    content = "This is a simple test."
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["This", "is", "a", "simple", "test"]
    assert tags == []


def test_word_extractor_html_tags():
    content = "<p>This is a <b>bold</b> statement.</p>"
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["This", "is", "a", "bold", "statement"]
    assert get_content_by_indices(content, tags) == ["<p>", "<b>", "</b>", "</p>"]


def test_word_extractor_math_symbols():
    content = "Let's consider the case where a < b and x > y."
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["Let's", "consider", "the", "case", "where", "a", "<", "b", "and", "x", ">", "y"]
    assert tags == []


def test_word_extractor_mixed_content():
    content = "<div>Python code: if x < 5 and y > 10:</div><p>This is a test.</p>"
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["Python", "code", "if", "x", "<", "5", "and", "y", ">", "10", "This", "is", "a", "test"]
    assert get_content_by_indices(content, tags) == ["<div>", "</div>", "<p>", "</p>"]


def test_word_extractor_empty_content():
    content = ""
    words, tags = parse_words(content)
    assert words == []
    assert tags == []


def test_word_extractor_only_html():
    content = "<p><br><hr></p>"
    words, tags = parse_words(content)
    assert words == []
    assert get_content_by_indices(content, tags) == ["<p>", "<br>", "<hr>", "</p>"]


def test_word_extractor_nested_tags():
    content = "<div><p>Nested <span>tags</span> here</p></div>"
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["Nested", "tags", "here"]
    assert get_content_by_indices(content, tags) == ["<div>", "<p>", "<span>", "</span>", "</p>", "</div>"]


def test_word_extractor_self_closing_tags():
    content = "An image <img src='test.jpg'/> and some <br/> text"
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["An", "image", "and", "some", "text"]
    assert get_content_by_indices(content, tags) == ["<img src='test.jpg'/>", "<br/>"]


def test_word_extractor_attributes_with_spaces():
    content = '<a href="https://example.com" title="Click here">Link</a>'
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["Link"]
    assert get_content_by_indices(content, tags) == ['<a href="https://example.com" title="Click here">', "</a>"]


def test_word_extractor_script_and_style_tags():
    content = """
    <style>
        body { font-size: 16px; }
    </style>
    <script>
        console.log("Hello");
    </script>
    <p>Visible text</p>
    """
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["Visible", "text"]
    assert get_content_by_indices(content, tags) == [
        '<style>\n        body { font-size: 16px; }\n    </style>',
        '<script>\n        console.log("Hello");\n    </script>',
        '<p>', '</p>'
    ]


def test_word_extractor_remove_html_and_adjust_indices():
    html_content = "<p>This is a <b>bold</b> statement.</p>"
    words, tags = parse_words(html_content)

    plain_text, adjusted_indices = HTMLWordExtractor.remove_html(html_content, words, tags)

    assert plain_text == "This is a bold statement."
    assert [plain_text[start:end] for start, end in adjusted_indices] == ["This", "is", "a", "bold", "statement"]


def test_word_extractor_remove_html_and_adjust_indices_with_excluded_tags():
    html_content = """
    <p>Visible text</p>
    <script>
        console.log("Hello");
    </script>
    <p>More text</p>
    """
    words, tags = parse_words(html_content)

    plain_text, adjusted_indices = HTMLWordExtractor.remove_html(html_content, words, tags)

    assert plain_text == "\n    Visible text\n    \n    More text\n    "
    assert [plain_text[start:end] for start, end in adjusted_indices] == ["Visible", "text", "More", "text"]


def test_word_extractor_remove_html_and_adjust_indices_with_nested_tags():
    html_content = "<div><p>Nested <span>tags</span> here</p></div>"
    words, tags = parse_words(html_content)

    plain_text, adjusted_indices = HTMLWordExtractor.remove_html(html_content, words, tags)

    assert plain_text == "Nested tags here"
    assert [plain_text[start:end] for start, end in adjusted_indices] == ["Nested", "tags", "here"]


def test_word_extractor_remove_html_and_adjust_indices_with_self_closing_tags():
    html_content = "An image <img src='test.jpg'/> and some <br/> text"
    words, tags = parse_words(html_content)

    plain_text, adjusted_indices = HTMLWordExtractor.remove_html(html_content, words, tags)

    assert plain_text == "An image  and some  text"
    assert [plain_text[start:end] for start, end in adjusted_indices] == ["An", "image", "and", "some", "text"]