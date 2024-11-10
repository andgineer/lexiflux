import allure
import pytest
from typing import List, Tuple, Dict
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage

from lexiflux.language.sentence_extractor_llm import break_into_sentences_llm, WORD_START_MARK, WORD_END_MARK, \
    SENTENCE_START_MARK, SENTENCE_END_MARK


def create_mock_llm_response(text: str, highlighted_word: str) -> str:
    """Create a mock LLM response that wraps the sentence containing the highlighted word."""
    # Find the highlighted word position
    start = text.find(highlighted_word)
    if start == -1:
        return text

    # Find sentence boundaries
    # Look back for sentence start (period + space or start of text)
    sentence_start = text.rfind('. ', 0, start)
    if sentence_start == -1:
        sentence_start = 0
    else:
        sentence_start += 2  # Skip the period and space

    # Look forward for sentence end (period or end of text)
    sentence_end = text.find('.', start)
    if sentence_end == -1:
        sentence_end = len(text)
    else:
        sentence_end += 1  # Include the period

    # Reconstruct text with sentence markers
    return (
            text[:sentence_start] +
            "[FRAGMENT]" +
            text[sentence_start:sentence_end] +
            "[/FRAGMENT]" +
            text[sentence_end:]
    )


class MockChain:
    def invoke(self, inputs):
        """Mock the chain's invoke method to properly format the response."""
        text = inputs['text']

        # Find the highlighted word position
        start = text.find(WORD_START_MARK)
        end = text.find(WORD_END_MARK)

        if start != -1 and end != -1:
            # Get the text before and after the highlighted word
            before = text[:start]
            highlighted = text[start:end + len(WORD_END_MARK)]
            after = text[end + len(WORD_END_MARK):]

            # Find sentence boundaries (simplified for testing)
            sentence_start = 0
            sentence_end = text.find('.')
            if sentence_end == -1:
                sentence_end = len(text)
            else:
                sentence_end += 1  # Include the period

            # Construct the response with proper sentence markers
            response = (
                    text[:sentence_start] +
                    SENTENCE_START_MARK +
                    text[sentence_start:sentence_end] +
                    SENTENCE_END_MARK +
                    text[sentence_end:]
            )
            return response

        return text


@pytest.fixture
def mock_llm_chain():
    """Fixture to mock the LangChain chain when skip_llm is True."""
    mock_chain = MockChain()
    with patch('lexiflux.language.sentence_extractor_llm.ChatPromptTemplate.from_messages') as mock_prompt:
        with patch('lexiflux.language.sentence_extractor_llm.ChatOpenAI') as mock_chat:
            with patch('lexiflux.language.sentence_extractor_llm.TextOutputParser') as mock_parser:
                # Create a mock chain that will be returned by the | operations
                chain = MagicMock()
                chain.invoke = mock_chain.invoke

                # Make the | operator return our mock chain
                mock_prompt.return_value.__or__.return_value.__or__.return_value = chain
                yield mock_chain


def validate_inputs(plain_text: str, word_slices: List[Tuple[int, int]], term_word_ids: List[int]) -> None:
    """Validate input parameters for break_into_sentences_llm."""
    if not plain_text:
        raise ValueError("Input text cannot be empty")

    if not word_slices:
        raise ValueError("Word slices list cannot be empty")

    if not term_word_ids:
        raise ValueError("Term word IDs list cannot be empty")

    if any(word_id >= len(word_slices) for word_id in term_word_ids):
        raise ValueError(f"Invalid highlighted word ID. Word IDs must be less than {len(word_slices)}")


@allure.epic('Book import')
@allure.feature('LLM: Break text into sentences')
@pytest.mark.parametrize("text, word_ids, highlighted_word_ids, expected_sentences, expected_word_to_sentence", [
    # Test case 1: Basic sentence
    (
            "The quick brown fox jumps over the lazy dog.",
            [(0, 3), (4, 9), (10, 15), (16, 19), (20, 25), (26, 30), (31, 34), (35, 39), (40, 43)],
            [4],  # "jumps"
            ["The quick brown fox jumps over the lazy dog."],
            {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0}
    ),
    # Test case 2: Multiple sentences with highlighted word in first sentence
    (
            "The quick brown fox jumps over the lazy dog. It was a sunny day.",
            [(0, 3), (4, 9), (10, 15), (16, 19), (20, 25), (26, 30), (31, 34), (35, 39), (40, 43),
             (45, 47), (48, 51), (52, 53), (54, 59), (60, 64)],
            [4],  # "jumps"
            ["The quick brown fox jumps over the lazy dog."],
            {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0}
    ),
])
def test_break_into_sentences_llm(
        text: str,
        word_ids: List[Tuple[int, int]],
        highlighted_word_ids: List[int],
        expected_sentences: List[str],
        expected_word_to_sentence: Dict[int, int],
        mock_llm_chain,
        request
):
    """Test break_into_sentences_llm with either real or mocked LLM based on skip_llm flag."""
    if request.config.getoption("--use-llm"):
        print("#" * 20, " Using real ChatGPT ", "#" * 20)
        with patch('lexiflux.language.sentence_extractor_llm.ChatOpenAI') as mock:
            mock.return_value = mock_llm_chain
            sentences, word_to_sentence = break_into_sentences_llm(text, word_ids, highlighted_word_ids)
    else:
        # Using the mock
        with patch('lexiflux.language.sentence_extractor_llm.validate_inputs', wraps=validate_inputs):
            sentences, word_to_sentence = break_into_sentences_llm(text, word_ids, highlighted_word_ids)


    assert sentences == expected_sentences, f"Expected {expected_sentences}, but got {sentences}"
    assert word_to_sentence == expected_word_to_sentence, \
        f"Expected {expected_word_to_sentence}, but got {word_to_sentence} for text: '{text}'"


@allure.epic('Book import')
@allure.feature('LLM: Break text into sentences')
@pytest.mark.parametrize("text, word_ids, highlighted_word_ids, expected_error", [
    # Test case for empty text
    ("", [], [0], "Input text cannot be empty"),
    # Test case for invalid highlighted word ID
    ("This is a test.", [(0, 4), (5, 7), (8, 9), (10, 14)], [5], "Invalid highlighted word ID"),
    # Test case for empty word_ids
    ("Test text", [], [0], "Word slices list cannot be empty"),
    # Test case for empty highlighted_word_ids
    ("Test text", [(0, 4)], [], "Term word IDs list cannot be empty"),
])
def test_break_into_sentences_edge_cases(
        text: str,
        word_ids: List[Tuple[int, int]],
        highlighted_word_ids: List[int],
        expected_error: str,
        mock_llm_chain,
        request
):
    """Test edge cases with either real or mocked LLM based on skip_llm flag."""
    if request.config.getoption("--use-llm"):
        with pytest.raises(ValueError) as exc_info:
            with patch('lexiflux.language.sentence_extractor_llm.validate_inputs', wraps=validate_inputs):
                break_into_sentences_llm(text, word_ids, highlighted_word_ids)
    else:
        with patch('lexiflux.language.sentence_extractor_llm.ChatOpenAI') as mock:
            mock.return_value = mock_llm_chain
            with pytest.raises(ValueError) as exc_info:
                break_into_sentences_llm(text, word_ids, highlighted_word_ids)

    assert expected_error in str(exc_info.value)