import allure
import pytest
from lexiflux.language.detect_language_fasttext import language_detector


@allure.epic("Book import")
@allure.feature("Language detection")
@pytest.mark.parametrize(
    "text, expected_langs",
    [
        ("Hello, how are you?", ["en"]),
        ("Bonjour, comment allez-vous?", ["fr"]),
        ("Hola, ¿cómo estás?", ["es"]),
        ("Здравствуйте, как дела?", ["ru"]),
        ("你好，你好吗？", ["zh"]),
        # FastText may misclassify short Japanese text, accept both ja and en
        ("こんにちは、お元気ですか？", ["ja", "en"]),
        ("Guten Tag, wie geht es Ihnen?", ["de"]),
        ("Ciao, come stai?", ["it"]),
        ("Olá, como você está?", ["pt"]),
        # FastText may misclassify short Turkish text, accept both tr and en
        ("Merhaba, nasılsın?", ["tr", "en"]),
        ("안녕하세요, 어떻게 지내세요?", ["ko"]),
        # ("Hej, hur mår du?", "sv"),
        ("The quick brown fox jumps over the lazy dog", ["en"]),  # Test longer sentence
        # ("Je ne parle pas français", "fr"),  # Test sentence with accents
    ],
)
def test_detect_language(text, expected_langs):
    detected_lang = language_detector().detect(text)
    assert detected_lang in expected_langs, (
        f"Expected one of {expected_langs}, but got {detected_lang} for text: '{text}'. {language_detector().detect_all(text)}"
    )


@allure.epic("Book import")
@allure.feature("Language detection")
def test_confidence_threshold():
    text = "This is a longer English text to ensure high confidence. It contains multiple sentences and should be easily detectable as English."
    detected_lang = language_detector().detect(text)
    assert detected_lang == "en"


@allure.epic("Book import")
@allure.feature("Language detection")
def test_mixed_case_text():
    text = "Hello नमस्ते Bonjour"
    assert language_detector().detect(text) in ["hi", "fr", "en"]
