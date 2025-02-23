import allure
import pytest
from unittest.mock import patch, MagicMock

from lexiflux.language.sentence_extractor_llm import (
    break_into_sentences_llm,
    WORD_START_MARK,
    WORD_END_MARK,
    SENTENCE_START_MARK,
    SENTENCE_END_MARK,
)


def create_mock_llm_response(text: str, highlighted_word: str) -> str:
    """Create a mock LLM response that wraps the sentence containing the highlighted word."""
    # Find the highlighted word position
    start = text.find(highlighted_word)
    if start == -1:
        return text

    # Find sentence boundaries
    # Look back for sentence start (period + space or start of text)
    sentence_start = text.rfind(". ", 0, start)
    if sentence_start == -1:
        sentence_start = 0
    else:
        sentence_start += 2  # Skip the period and space

    # Look forward for sentence end (period or end of text)
    sentence_end = text.find(".", start)
    if sentence_end == -1:
        sentence_end = len(text)
    else:
        sentence_end += 1  # Include the period

    # Reconstruct text with sentence markers
    return (
        text[:sentence_start]
        + "[FRAGMENT]"
        + text[sentence_start:sentence_end]
        + "[/FRAGMENT]"
        + text[sentence_end:]
    )


class MockChain:
    def invoke(self, inputs):
        """Mock the chain's invoke method to properly format the response."""
        text = inputs["text"]

        # Find the highlighted word position
        start = text.find(WORD_START_MARK)
        end = text.find(WORD_END_MARK)

        if start != -1 and end != -1:
            # Get the text before and after the highlighted word
            before = text[:start]
            highlighted = text[start : end + len(WORD_END_MARK)]
            after = text[end + len(WORD_END_MARK) :]

            # Find sentence boundaries (simplified for testing)
            sentence_start = 0
            sentence_end = text.find(".")
            if sentence_end == -1:
                sentence_end = len(text)
            else:
                sentence_end += 1  # Include the period

            # Construct the response with proper sentence markers
            response = (
                text[:sentence_start]
                + SENTENCE_START_MARK
                + text[sentence_start:sentence_end]
                + SENTENCE_END_MARK
                + text[sentence_end:]
            )
            return response

        return text


@pytest.fixture
def mock_llm_chain(request):
    """Fixture to mock the LangChain chain when skip_llm is True."""
    if request.config.getoption("--use-llm"):
        # Don't mock anything when using real LLM
        yield None
    else:
        mock_chain = MockChain()
        with patch(
            "lexiflux.language.sentence_extractor_llm.ChatPromptTemplate.from_messages"
        ) as mock_prompt:
            with patch("lexiflux.language.sentence_extractor_llm.ChatOpenAI") as mock_chat:
                with patch(
                    "lexiflux.language.sentence_extractor_llm.TextOutputParser"
                ) as mock_parser:
                    chain = MagicMock()
                    chain.invoke = mock_chain.invoke
                    mock_prompt.return_value.__or__.return_value.__or__.return_value = chain
                    yield chain


@allure.epic("Book import")
@allure.feature("LLM: Break text into sentences")
@pytest.mark.parametrize(
    "text, word_ids, highlighted_word_ids, expected_sentences, expected_word_to_sentence",
    [
        # Test case 1: Basic sentence
        (
            "The quick brown fox jumps over the lazy dog.",
            [(0, 3), (4, 9), (10, 15), (16, 19), (20, 25), (26, 30), (31, 34), (35, 39), (40, 43)],
            [4],  # "jumps"
            ["The quick brown fox jumps over the lazy dog."],
            {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0},
        ),
        # Test case 2: Multiple sentences with highlighted word in first sentence
        (
            "The quick brown fox jumps over the lazy dog. It was a sunny day.",
            [
                (0, 3),
                (4, 9),
                (10, 15),
                (16, 19),
                (20, 25),
                (26, 30),
                (31, 34),
                (35, 39),
                (40, 43),
                (45, 47),
                (48, 51),
                (52, 53),
                (54, 59),
                (60, 64),
            ],
            [4],  # "jumps"
            ["The quick brown fox jumps over the lazy dog."],
            {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0},
        ),
    ],
)
def test_break_into_sentences_llm(
    text: str,
    word_ids: list[tuple[int, int]],
    highlighted_word_ids: list[int],
    expected_sentences: list[str],
    expected_word_to_sentence: dict[int, int],
    mock_llm_chain,
):
    """Test break_into_sentences_llm with either real or mocked LLM based on skip_llm flag."""
    sentences, word_to_sentence = break_into_sentences_llm(text, word_ids, highlighted_word_ids)

    assert sentences == expected_sentences, f"Expected {expected_sentences}, but got {sentences}"
    assert word_to_sentence == expected_word_to_sentence, (
        f"Expected {expected_word_to_sentence}, but got {word_to_sentence} for text: '{text}'"
    )


@allure.epic("Book import")
@allure.feature("LLM: Break text into sentences")
@pytest.mark.parametrize(
    "text, word_ids, highlighted_word_ids, expected_error",
    [
        # Test case for empty text
        ("", [], [0], "Input text cannot be empty"),
        # Test case for invalid highlighted word ID
        ("This is a test.", [(0, 4), (5, 7), (8, 9), (10, 14)], [5], "Invalid highlighted word ID"),
        # Test case for empty word_ids
        ("Test text", [], [0], "Word slices list cannot be empty"),
        # Test case for empty highlighted_word_ids
        ("Test text", [(0, 4)], [], "Term word IDs list cannot be empty"),
    ],
)
def test_break_into_sentences_edge_cases(
    text: str,
    word_ids: list[tuple[int, int]],
    highlighted_word_ids: list[int],
    expected_error: str,
    mock_llm_chain,
):
    """Test edge cases with either real or mocked LLM based on skip_llm flag."""
    with pytest.raises(ValueError) as exc_info:
        break_into_sentences_llm(text, word_ids, highlighted_word_ids)

    assert expected_error in str(exc_info.value)
