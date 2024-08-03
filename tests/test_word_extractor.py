import allure

from lexiflux.language.word_extractor import parse_words, WordTokenizer


def get_content_by_indices(content, indices):
    return [content[start:end] for start, end in indices]


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_simple_text():
    content = "This is a simple test."
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["This", "is", "a", "simple", "test"]
    assert tags == []


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_html_tags():
    content = "<p>This is a <b>bold</b> statement.</p>"
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["This", "is", "a", "bold", "statement"]
    assert get_content_by_indices(content, tags) == ["<p>", "<b>", "</b>", "</p>"]


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_math_symbols():
    content = "Let's consider the case where a < b and x > y."
    words, tags = parse_words(content, tokenizer=WordTokenizer.NAIVE)
    assert get_content_by_indices(content, words) == ["Let", "s", "consider", "the", "case", "where", "a", "b", "and", "x", "y"]
    assert tags == []


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_mixed_content():
    content = "<div>Python code: if x < 5 and y > 10:</div><p>This is a test.</p>"
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["Python", "code", "if", "x", "5", "and", "y", "10", "This", "is", "a", "test"]
    assert get_content_by_indices(content, tags) == ["<div>", "</div>", "<p>", "</p>"]


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_empty_content():
    content = ""
    words, tags = parse_words(content)
    assert words == []
    assert tags == []


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_only_html():
    content = "<p><br><hr></p>"
    words, tags = parse_words(content)
    assert words == []
    assert get_content_by_indices(content, tags) == ["<p>", "<br>", "<hr>", "</p>"]


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_nested_tags():
    content = "<div><p>Nested <span>tags</span> here</p></div>"
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["Nested", "tags", "here"]
    assert get_content_by_indices(content, tags) == ["<div>", "<p>", "<span>", "</span>", "</p>", "</div>"]


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_self_closing_tags():
    content = "An image <img src='test.jpg'/> and some <br/> text"
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["An", "image", "and", "some", "text"]
    assert get_content_by_indices(content, tags) == ["<img src='test.jpg'/>", "<br/>"]


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_attributes_with_spaces():
    content = '<a href="https://example.com" title="Click here">Link</a>'
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["Link"]
    assert get_content_by_indices(content, tags) == ['<a href="https://example.com" title="Click here">', "</a>"]


@allure.epic('Book import')
@allure.feature('Word extraction')
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
        '<style>', '\n        body { font-size: 16px; }\n    ', '</style>',
        '<script>', '\n        console.log("Hello");\n    ', '</script>', '<p>', '</p>'
    ]


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_with_entity_and_charref():
    content = "Entity: &lt; CharRef: &#60;"
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["Entity", "CharRef"]
    assert get_content_by_indices(content, tags) == []


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_with_cdata():
    content = "<![CDATA[This is CDATA content]]>Regular content"
    words, tags = parse_words(content)
    assert get_content_by_indices(content, words) == ["Regular", "content"]
    assert get_content_by_indices(content, tags) == ["<![CDATA[This is CDATA content]]>"]


@allure.epic('Book import')
@allure.feature('Word extraction')
def test_word_extractor_alice():
    content = "1 <br/> <br/> <br/> <br/> ALICE&#x27;S ADVENTURES IN <br/> <br/>"
    words, tags = parse_words(content, tokenizer=WordTokenizer.NAIVE)
    assert get_content_by_indices(content, words) == ["1", "ALICE", "S", "ADVENTURES", "IN"]
    assert get_content_by_indices(content, tags) == ["<br/>", "<br/>", "<br/>", "<br/>", "<br/>", "<br/>"]