import pytest
from lexiflux.language.detect_language_fasttext import detect_language


@pytest.mark.parametrize("text, expected_lang", [
    ("Hello, how are you?", "en"),
    ("Bonjour, comment allez-vous?", "fr"),
    ("Hola, ¿cómo estás?", "es"),
    ("Здравствуйте, как дела?", "ru"),
    ("你好，你好吗？", "zh"),
    ("こんにちは、お元気ですか？", "ja"),
    ("Guten Tag, wie geht es Ihnen?", "de"),
    ("Ciao, come stai?", "it"),
    ("Olá, como você está?", "pt"),
    ("Merhaba, nasılsın?", "tr"),
    ("안녕하세요, 어떻게 지내세요?", "ko"),
    ("Hej, hur mår du?", "sv"),
    ("The quick brown fox jumps over the lazy dog", "en"),  # Test longer sentence
    ("Je ne parle pas français", "fr"),  # Test sentence with accents
])
def test_detect_language(text, expected_lang):
    detected_lang, confidence = detect_language(text)
    assert detected_lang == expected_lang, f"Expected {expected_lang}, but got {detected_lang} for text: '{text}'"
    assert 0 <= confidence <= 1.00005, f"Confidence should be between 0 and 1, but got {confidence}"

def test_confidence_threshold():
    text = "This is a longer English text to ensure high confidence. It contains multiple sentences and should be easily detectable as English."
    detected_lang, confidence = detect_language(text)
    assert detected_lang == "en"
    assert confidence > 0.9, f"Expected confidence > 0.9 for clear English text, but got {confidence}"


def test_mixed_case_text():
    text = "Hello नमस्ते Bonjour"
    detected_lang, confidence = detect_language(text)
    assert confidence < 0.8, f"Expected lower confidence, but got {confidence}"


def test_only_numbers():
    text = "123 456 789"
    detected_lang, confidence = detect_language(text)
    assert confidence < 0.8, f"Expected lower confidence, but got {confidence}"

def test_only_punctuation():
    text = "!!!"
    detected_lang, confidence = detect_language(text)
    assert confidence < 0.8, f"Expected lower confidence, but got {confidence}"


def test_only_special_characters():
    text = "🎉🎊🎈"
    detected_lang, confidence = detect_language(text)
    assert confidence < 0.8, f"Expected lower confidence, but got {confidence}"


def test_very_short_text():
    text = "Hi"
    detected_lang, confidence = detect_language(text)
    assert confidence < 0.8, f"Expected lower confidence, but got {confidence}"


def test_empty_text():
    text = ""
    detected_lang, confidence = detect_language(text)
    assert confidence <= 0.8, f"Expected lower confidence, but got {confidence}"
