import allure
import pytest
from typing import List, Tuple, Dict

from lexiflux.language.sentence_extractor_llm import break_into_sentences

# This tests use real LLM, need KEY and spend money. Skip them by default.
SKIP_LLM = True


@allure.epic('Book import')
@allure.feature('LLM: Break text into sentences')
@pytest.mark.skipif(SKIP_LLM, reason="Skipping LLM tests")
@pytest.mark.parametrize("text, word_ids, highlighted_word_id, expected_sentences, expected_word_to_sentence", [
    # Test case 1: Basic sentence
    (
            "The quick brown fox jumps over the lazy dog.",
            [(0, 3), (4, 9), (10, 15), (16, 19), (20, 25), (26, 30), (31, 34), (35, 39), (40, 43)],
            3,
            ["The quick brown fox jumps over the lazy dog."],
            {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0}
    ),
    # Test case 2: Multiple sentences
    (
            "The quick brown fox jumps over the lazy dog. It was a sunny day in the forest.",
            [(0, 3), (4, 9), (10, 15), (16, 19), (20, 25), (26, 30), (31, 34), (35, 39), (40, 43), (44, 46),
             (47, 50), (51, 52), (53, 55), (56, 59), (60, 61), (62, 67), (68, 71), (72, 74), (75, 79),
             (80, 87), (87, 88)],
            3,
            ["The quick brown fox jumps over the lazy dog."],
            {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0}
    ),
    # Test case 3: Complex sentence with dependent clause
    (
            "Although it was raining, the determined hiker continued his journey through the dense forest.",
            [(0, 8), (9, 11), (12, 15), (16, 23), (24, 27), (28, 38), (39, 44), (45, 54), (55, 58), (59, 66),
             (67, 74), (75, 78), (79, 84), (85, 91), (91, 92)],
            5,
            ["Although it was raining, the determined hiker continued his journey through the dense forest."],
            {i: 0 for i in range(15)}
    ),
    # Test case 4: Sentence with quotation marks
    (
            '"The early bird catches the worm," said the wise old owl.',
            [(0, 1), (1, 4), (5, 10), (11, 15), (16, 23), (24, 27), (28, 32), (32, 33), (34, 38), (39, 42),
             (43, 47), (48, 51), (52, 55), (55, 56)],
            2,
            ['"The early bird catches the worm," said the wise old owl.'],
            {i: 0 for i in range(14)}
    ),
    # Test case 5: Sentence with semicolon
    (
            "I love programming; it's both challenging and rewarding.",
            [(0, 1), (2, 6), (7, 18), (18, 19), (20, 23), (23, 24), (25, 29), (30, 41), (42, 45), (46, 55), (55, 56)],
            1,
            ["I love programming; it's both challenging and rewarding."],
            {i: 0 for i in range(11)}
    ),
])
def test_break_into_sentences_llm(
        text: str,
        word_ids: List[Tuple[int, int]],
        highlighted_word_id: int,
        expected_sentences: List[str],
        expected_word_to_sentence: Dict[int, int]
):
    sentences, word_to_sentence = break_into_sentences(text, word_ids, highlighted_word_id)

    assert sentences == expected_sentences, f"Expected {expected_sentences}, but got {sentences}"
    assert word_to_sentence == expected_word_to_sentence, f"Expected {expected_word_to_sentence}, but got {word_to_sentence} for text: '{text}'"


@allure.epic('Book import')
@allure.feature('LLM: Break text into sentences')
@pytest.mark.skipif(SKIP_LLM, reason="Skipping LLM tests")
@pytest.mark.parametrize("text, word_ids, highlighted_word_id", [
    # Test case 6: Empty text
    ("", [], 0),
    # Test case 7: Text without highlighted word
    ("This is a test.", [(0, 4), (5, 7), (8, 9), (10, 14), (14, 15)], 5),
])
def test_break_into_sentences_edge_cases(
        text: str,
        word_ids: List[Tuple[int, int]],
        highlighted_word_id: int
):
    with pytest.raises(ValueError) as exc_info:
        break_into_sentences(text, word_ids, highlighted_word_id)
        assert "Highlighted word ID" in str(exc_info)
