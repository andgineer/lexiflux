from unittest.mock import patch

import allure

from lexiflux.language.detect_language_detectlanguage import language_detector

@allure.epic('Book import')
@allure.feature('Language detection')
@patch('lexiflux.language.detect_language_detectlanguage.language_detector')
def test_detect_language_key_error(mock_single_detection, monkeypatch, caplog):
    monkeypatch.delenv("DETECTLANGUAGE_API_KEY", raising=False)

    result = language_detector().detect("Test text.")

    assert "Please get your API Key" in caplog.text
    assert result == "en"  # Default fallback language


@allure.epic('Book import')
@allure.feature('Language detection')
@patch('lexiflux.language.detect_language_detectlanguage.language_detector')
def test_detect_language_exception(mock_single_detection, monkeypatch, caplog):
    monkeypatch.setenv("DETECTLANGUAGE_API_KEY", "dummy_key")
    # Simulate an exception being raised by single_detection
    mock_single_detection.side_effect = Exception("API failure")

    result = language_detector().detect("Test text.")

    assert "Failed to detect language" in caplog.text
    assert result == "en"  # Default fallback language
