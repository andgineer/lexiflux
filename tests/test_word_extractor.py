from lexiflux.word_extractor import parse_words

def get_words_by_indices(content, indices):
    return [content[start:end] for start, end in indices]


def test_simple_text():
    content = "This is a simple test."
    words = get_words_by_indices(content, parse_words(content))
    assert words == ["This", "is", "a", "simple", "test"]
    assert len(words) == 5

def test_html_tags():
    content = "<p>This is a <b>bold</b> statement.</p>"
    words = get_words_by_indices(content, parse_words(content))
    assert words == ["This", "is", "a", "bold", "statement"]
    assert len(words) == 5

def test_math_symbols():
    content = "Let's consider the case where a < b and x > y."
    words = get_words_by_indices(content, parse_words(content))
    assert words == ["Let's", "consider", "the", "case", "where", "a", "<", "b", "and", "x", ">", "y"]
    assert len(words) == 12

def test_mixed_content():
    content = "<div>Python code: if x < 5 and y > 10:</div><p>This is a test.</p>"
    words = get_words_by_indices(content, parse_words(content))
    assert words == ["Python", "code", "if", "x", "<", "5", "and", "y", ">", "10", "This", "is", "a", "test"]
    assert len(words) == 14

def test_empty_content():
    content = ""
    words = get_words_by_indices(content, parse_words(content))
    assert words == []
    assert len(words) == 0

def test_only_html():
    content = "<p><br><hr></p>"
    words = get_words_by_indices(content, parse_words(content))
    assert words == []
    assert len(words) == 0

def test_nested_tags():
    content = "<div><p>Nested <span>tags</span> here</p></div>"
    words = get_words_by_indices(content, parse_words(content))
    assert words == ["Nested", "tags", "here"]
    assert len(words) == 3

def test_self_closing_tags():
    content = "An image <img src='test.jpg'/> and some <br/> text"
    words = get_words_by_indices(content, parse_words(content))
    assert words == ["An", "image", "and", "some", "text"]
    assert len(words) == 5

def test_attributes_with_spaces():
    content = '<a href="https://example.com" title="Click here">Link</a>'
    words = get_words_by_indices(content, parse_words(content))
    assert words == ["Link"]
    assert len(words) == 1

def test_script_and_style_tags():
    content = """
    <style>
        body { font-size: 16px; }
    </style>
    <script>
        console.log("Hello");
    </script>
    <p>Visible text</p>
    """
    words = get_words_by_indices(content, parse_words(content))
    assert words == ["Visible", "text"]
    assert len(words) == 2