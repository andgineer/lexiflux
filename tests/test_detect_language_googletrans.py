import allure
import pytest
from time import sleep
from typing import List

from lexiflux.language.detect_language_googletrans import language_detector

SKIP_GOOGLETRANS_TESTS = True


def make_api_call_with_retry(func, *args, max_retries: int = 3, delay: float = 1.0):
    """Helper function to retry API calls with delay."""
    for attempt in range(max_retries):
        try:
            return func(*args)
        except Exception:
            if attempt == max_retries - 1:
                raise
            sleep(delay)


@allure.epic("Book import")
@allure.feature("Language detection")
@pytest.mark.skipif(SKIP_GOOGLETRANS_TESTS, reason="Skipping Google Translate tests")
@pytest.mark.parametrize(
    "text, expected_lang",
    [
        ("Hello, how are you?", "en"),
        ("Bonjour, comment allez-vous?", "fr"),
        ("Hola, ¿cómo estás?", "es"),
        ("Здравствуйте, как дела?", "ru"),
        ("你好，你好吗？", "zh-cn"),  # Note: Google may return zh-cn instead of zh
        ("こんにちは、お元気ですか？", "ja"),
        ("Guten Tag, wie geht es Ihnen?", "de"),
        ("Ciao, come stai?", "it"),
        ("Olá, como você está?", "pt"),
        ("Merhaba, nasılsın?", "tr"),
        ("안녕하세요, 어떻게 지내세요?", "ko"),
        # Using longer texts to ensure better accuracy
        (
            "The quick brown fox jumps over the lazy dog. This is a longer English text to ensure accuracy.",
            "en",
        ),
        ("Je ne parle pas français. C'est une phrase plus longue pour assurer la précision.", "fr"),
    ],
)
def test_detect_language_real_api(text: str, expected_lang: str):
    """Test language detection with real API calls to Google Translate."""
    detected_lang = make_api_call_with_retry(language_detector().detect, text)
    assert detected_lang == expected_lang, (
        f"Expected {expected_lang}, but got {detected_lang} for text: '{text}'"
    )
    # Add small delay to avoid hitting rate limits
    sleep(0.5)


@allure.epic("Book import")
@allure.feature("Language detection")
@pytest.mark.skipif(SKIP_GOOGLETRANS_TESTS, reason="Skipping Google Translate tests")
def test_confidence_score_real_api():
    """Test that confidence scores are returned and are within expected range."""
    text = (
        "This is a longer English text to ensure high confidence. It contains multiple sentences."
    )
    langs, scores = make_api_call_with_retry(language_detector().detect_all, text)

    assert isinstance(langs, List), "Expected list of language codes"
    assert isinstance(scores, List), "Expected list of confidence scores"
    assert len(langs) >= 1, "Expected at least one language prediction"
    assert len(scores) >= 1, "Expected at least one confidence score"
    assert all(0 <= score <= 1 for score in scores), "Confidence scores should be between 0 and 1"
    assert langs[0] == "en", f"Expected English (en) as top prediction, got {langs[0]}"
    assert scores[0] > 0.8, f"Expected high confidence score (>0.8), got {scores[0]}"


@allure.epic("Book import")
@allure.feature("Language detection")
@pytest.mark.skipif(SKIP_GOOGLETRANS_TESTS, reason="Skipping Google Translate tests")
def test_mixed_language_text_real_api():
    """Test detection with text containing multiple languages."""
    text = "Hello नमस्ते Bonjour"  # Mix of English, Hindi, and French
    result = make_api_call_with_retry(language_detector().detect, text)
    assert result in ["hi", "fr", "en"], f"Expected one of ['hi', 'fr', 'en'], but got {result}"


@allure.epic("Book import")
@allure.feature("Language detection")
@pytest.mark.skipif(SKIP_GOOGLETRANS_TESTS, reason="Skipping Google Translate tests")
def test_api_stability():
    """Test API stability by making multiple calls with the same text."""
    text = "Hello, world!"
    results = []
    for _ in range(3):
        lang = make_api_call_with_retry(language_detector().detect, text)
        results.append(lang)
        sleep(0.5)  # Add delay between calls

    # All results should be the same
    assert len(set(results)) == 1, (
        f"Expected consistent results across multiple API calls, got: {results}"
    )
    assert results[0] == "en", f"Expected 'en', got {results[0]}"


@allure.epic("Book import")
@allure.feature("Language detection")
@pytest.mark.skipif(SKIP_GOOGLETRANS_TESTS, reason="Skipping Google Translate tests")
def test_error_handling():
    """Test error handling with invalid input."""
    with pytest.raises(Exception):
        language_detector().detect("")  # Empty text should raise an error

    with pytest.raises(Exception):
        language_detector().detect(" " * 5000)  # Very long whitespace
