import allure
import pytest
from lexiflux.language.detect_language_fasttext import language_detector


@allure.epic('Book import')
@allure.feature('Language detection')
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
    # ("Hej, hur mår du?", "sv"),
    ("The quick brown fox jumps over the lazy dog", "en"),  # Test longer sentence
    # ("Je ne parle pas français", "fr"),  # Test sentence with accents
])
def test_detect_language(text, expected_lang):
    detected_lang = language_detector().detect(text)
    assert detected_lang == expected_lang, f"Expected {expected_lang}, but got {detected_lang} for text: '{text}'. {language_detector().detect_all(text)}"


@allure.epic('Book import')
@allure.feature('Language detection')
def test_confidence_threshold():
    text = "This is a longer English text to ensure high confidence. It contains multiple sentences and should be easily detectable as English."
    detected_lang = language_detector().detect(text)
    assert detected_lang == "en"


@allure.epic('Book import')
@allure.feature('Language detection')
def test_mixed_case_text():
    text = "Hello नमस्ते Bonjour"
    assert language_detector().detect(text) in ["hi", "fr", "en"]



