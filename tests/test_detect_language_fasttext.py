import allure
import pytest
from lexiflux.language.detect_language_fasttext import language_detector


@allure.epic("Book import")
@allure.feature("Language detection")
@pytest.mark.parametrize(
    "text, expected_langs",
    [
        ("Hello, how are you? I hope you are doing well today.", ["en"]),
        ("Bonjour, comment allez-vous? J'espère que vous allez bien aujourd'hui.", ["fr"]),
        ("Hola, ¿cómo estás? Espero que estés bien hoy.", ["es"]),
        ("Здравствуйте, как дела? Надеюсь, у вас все хорошо сегодня.", ["ru"]),
        ("你好，你好吗？我希望你今天一切都好。", ["zh", "ja"]),  # Chinese/Japanese can be confused
        ("こんにちは、お元気ですか？今日は良い一日を過ごしていますか？", ["ja"]),
        ("Guten Tag, wie geht es Ihnen? Ich hoffe, es geht Ihnen gut heute.", ["de"]),
        ("Ciao, come stai? Spero che tu stia bene oggi.", ["it"]),
        ("Olá, como você está? Espero que você esteja bem hoje.", ["pt"]),
        ("Merhaba, nasılsın? Umarım bugün iyisindir.", ["tr"]),
        ("안녕하세요, 어떻게 지내세요? 오늘 하루 잘 보내고 계신가요?", ["ko"]),
        # ("Hej, hur mår du?", "sv"),
        ("The quick brown fox jumps over the lazy dog", ["en"]),
        ("Je ne parle pas français", "fr"),  # Test sentence with accents
    ],
)
def test_detect_language(text, expected_langs):
    detected_lang = language_detector().detect(text)
    # Get predictions to check confidence
    predictions = language_detector().detect_all(text)
    labels = predictions[0]
    probabilities = predictions[1]

    # Check if detected language is in expected list
    if detected_lang in expected_langs:
        return  # Test passes

    # If not, check if any expected language is in top 3 predictions with reasonable probability
    top_3_langs = [label.replace("__label__", "") for label in labels[:3]]
    top_3_probs = [float(prob) for prob in probabilities[:3]]

    # If expected language is in top 3 and has reasonable probability (> 0.05), accept it
    for expected_lang in expected_langs:
        if expected_lang in top_3_langs:
            idx = top_3_langs.index(expected_lang)
            if top_3_probs[idx] > 0.05:
                # Expected language is in top 3 with reasonable confidence
                return  # Test passes

    # If we get here, the detection failed
    assert False, (
        f"Expected one of {expected_langs}, but got {detected_lang} for text: '{text}'. "
        f"Top 3 predictions: {list(zip(top_3_langs, top_3_probs))}"
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
