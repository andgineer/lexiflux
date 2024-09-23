import pytest
import allure
from lexiflux.models import BookPage
from lexiflux.language.llm import Llm


@pytest.fixture
def book_page_with_content(book):
    content = "This is a test page. It contains some words and punctuation! Here's another sentence."
    page = BookPage.objects.create(number=100, content=content, book=book)
    page.save()
    return page


@pytest.fixture
def llm_instance():
    return Llm()


@allure.epic('Language Processing')
@allure.feature('Term and Sentence Marking')
def test_mark_term_and_sentence(book_page_with_content, llm_instance):
    page = book_page_with_content
    llm = llm_instance

    # Prepare test data
    data = {
        "text": page.content,
        "book_code": page.book.code,
        "book_page_number": page.number,
        "word_slices": page.words,
        "term_word_ids": [3, 4],  # "test page"
        "text_language": page.book.language.google_code,
        "start_word_id": 0,
    }

    # Call the method
    result = llm.mark_term_and_sentence(llm.hashable_dict(data), context_words=5)

    marked_text = result
    print(f"Marked text: {marked_text}")

    assert "[FRAGMENT]This is a [HIGHLIGHT]test page[/HIGHLIGHT][/FRAGMENT]. It contains some words and punctuation" == marked_text

    # Check if context is included
    # assert "Here's another sentence." in marked_text

    # Test with different term and context
    data["term_word_ids"] = [7, 8]  # "some words"
    data["start_word_id"] = 5  # Start from "contains"
    result = llm.mark_term_and_sentence(llm.hashable_dict(data), context_words=3)

    marked_text = result
    print(f"Marked text (different term): {marked_text}")

    # Check if the correct sentence is marked
    assert "This is a test page. [FRAGMENT]It contains [HIGHLIGHT]some words[/HIGHLIGHT] and punctuation[/FRAGMENT]! Here's another sentence" == marked_text


@pytest.mark.parametrize("term_word_ids, expected_term", [
    ([0, 1], "This is"),
    ([3, 4], "test page"),
    ([7, 8, 9], "some words and"),
])
def test_mark_term_and_sentence_different_terms(book_page_with_content, llm_instance, term_word_ids, expected_term):
    page = book_page_with_content
    llm = llm_instance

    data = {
        "text": page.content,
        "book_code": page.book.code,
        "book_page_number": page.number,
        "word_slices": page.words,
        "term_word_ids": term_word_ids,
        "text_language": page.book.language.google_code,
        "start_word_id": 0,
    }

    result = llm.mark_term_and_sentence(llm.hashable_dict(data), context_words=5)
    marked_text = result
    print(f"Marked text for term '{expected_term}': {marked_text}")

    assert f"[HIGHLIGHT]{expected_term}[/HIGHLIGHT]" in marked_text

@pytest.mark.parametrize("context_words", [3, 5, 10])
def test_mark_term_and_sentence_different_context(book_page_with_content, llm_instance, context_words):
    page = book_page_with_content
    llm = llm_instance

    data = {
        "text": page.content,
        "book_code": page.book.code,
        "book_page_number": page.number,
        "word_slices": page.words,
        "term_word_ids": [3, 4],  # "test page"
        "text_language": page.book.language.google_code,
        "start_word_id": 0,
    }

    result = llm.mark_term_and_sentence(llm.hashable_dict(data), context_words=context_words)
    marked_text = result
    print(f"Marked text with context_words={context_words}: {marked_text}")

    # Count words before and after the term
    before_term = marked_text.split("[HIGHLIGHT]")[0].split()
    after_term = marked_text.split("[/HIGHLIGHT]")[1].split()

    assert len(before_term) >= min(context_words, 3)  # 3 is the number of words before "test page"
    assert len(after_term) >= context_words
