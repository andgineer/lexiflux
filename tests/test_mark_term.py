import pytest
import allure
from unittest.mock import patch, MagicMock, PropertyMock
from lexiflux.models import BookPage, Book
from lexiflux.language.llm import Llm
from lexiflux.language.sentence_extractor_llm import (
    SENTENCE_START_MARK,
    SENTENCE_END_MARK,
    WORD_START_MARK,
    WORD_END_MARK,
)


@pytest.fixture
def mock_book_page(book):
    page = BookPage.objects.get(book=book, number=1)
    content = "Word1 word2. Word3 word4. Word5 word6 word7. Word8 word9. Word10 word11 word12."

    words_cache = [
        (0, 5), (6, 11), (13, 18), (19, 24), (26, 31),  # 0 - 4
        (32, 37), (38, 43), (45, 50), (51, 56), (58, 64),  # 5 - 9
        (65, 71), (72, 78)
    ]

    word_sentence_mapping_cache = {
        0: 0, 1: 0, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 3, 8: 3, 9: 4, 10: 4, 11: 4
    }

    with patch('lexiflux.models.BookPage.words', new_callable=PropertyMock) as mock_words, \
            patch('lexiflux.models.BookPage.word_sentence_mapping',
                  new_callable=PropertyMock) as mock_word_sentence_mapping, patch('lexiflux.models.BookPage.content',
                  new_callable=PropertyMock) as mock_content:
        mock_words.return_value = words_cache
        mock_word_sentence_mapping.return_value = word_sentence_mapping_cache
        mock_content.return_value = content
        yield page


@pytest.fixture
def llm_instance():
    return Llm()


@allure.epic('Language Processing')
@allure.feature('Term and Sentence Marking')
def test_mark_term_and_sentence_success(mock_book_page, llm_instance):
    # Prepare test data
    data = {
        "book_code": mock_book_page.book.code,
        "book_page_number": mock_book_page.number,
        "term_word_ids": [4, 5],  # "Word5 word6"
    }

    # Call the method
    result = llm_instance.mark_term_and_sentence(llm_instance.hashable_dict(data), context_words=2)

    expected_result = (
        f"Word3 word4. {SENTENCE_START_MARK}{WORD_START_MARK}Word5 word6{WORD_END_MARK} "
        f"word7{SENTENCE_END_MARK}. Word8 word9"
    )

    assert result == expected_result

    # Test with different term and context
    data["term_word_ids"] = [9, 10]  # "Word10 word11"
    result = llm_instance.mark_term_and_sentence(llm_instance.hashable_dict(data), context_words=3)

    expected_result = (
        f"Word5 word6 word7. Word8 word9. {SENTENCE_START_MARK}{WORD_START_MARK}Word10 "
        f"word11{WORD_END_MARK} word12{SENTENCE_END_MARK}"
    )

    assert result == expected_result


@pytest.mark.parametrize("term_word_ids, expected_term", [
    ([0, 1], "Word1 word2"),
    ([4, 5], "Word5 word6"),
    ([9, 10, 11], "Word10 word11 word12"),
])
def test_mark_term_and_sentence_different_terms(mock_book_page, llm_instance, term_word_ids, expected_term):
    data = {
        "book_code": mock_book_page.book.code,
        "book_page_number": mock_book_page.number,
        "term_word_ids": term_word_ids,
    }

    result = llm_instance.mark_term_and_sentence(llm_instance.hashable_dict(data), context_words=2)
    print(f"Marked text for term '{expected_term}': {result}")

    assert f"{WORD_START_MARK}{expected_term}{WORD_END_MARK}" in result


@pytest.mark.parametrize("context_words, expected_words_before, expected_words_after", [
    (1, 2, 0),  # include word4(+3 in the same sentence) and word7 (in the same sentence as term
    (2, 2, 3),  # include word3 and word8 (+9 in the same sentence)
    (5, 4, 6),  # include word1 and word11 (plus ".")
])
def test_mark_term_and_sentence_different_context(mock_book_page, llm_instance, context_words, expected_words_before,
                                                  expected_words_after):
    data = {
        "book_code": mock_book_page.book.code,
        "book_page_number": mock_book_page.number,
        "term_word_ids": [4, 5],  # "Word5 word6"
    }

    result = llm_instance.mark_term_and_sentence(llm_instance.hashable_dict(data), context_words=context_words).replace(WORD_START_MARK, "").replace(WORD_END_MARK, "")
    print(f"Marked text with context_words={context_words}: {result}")

    words_before = result.split(SENTENCE_START_MARK)[0].split()
    words_after = result.split(SENTENCE_END_MARK)[1].split()

    assert len(words_before) == expected_words_before
    assert len(words_after) == expected_words_after