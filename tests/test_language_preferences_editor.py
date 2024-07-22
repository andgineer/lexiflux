import pytest
from django.urls import reverse
import allure
from tests.conftest import USER_PASSWORD
from tests.page_models.language_preferences_page import LanguagePreferencesPage


@allure.epic('End-to-end (selenium)')
@allure.feature('Language Preferences')
@allure.story('Inline Translation Editor')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_language_preferences_inline_translation(browser, approved_user, caplog, client):
    browser.login(approved_user, USER_PASSWORD)
    browser.goto(reverse('language-preferences'))

    page = LanguagePreferencesPage(browser)
    page.wait_for_page_load()
    browser.take_screenshot("Initial")

    assert "Language Tool Preferences" in page.get_page_title()
    assert "English" in page.get_selected_language()

    # Set Inline Translation Type to Translate and save
    page.open_inline_translation_editor()
    assert page.select_inline_translation_type("Translate") == "Translate"
    page.select_model()
    browser.take_screenshot("Before Inline Translation type Translation Save")
    page.save_changes()

    inline_translation_info = page.get_inline_translation_info()
    assert "Type:" in inline_translation_info
    assert "Translate" in inline_translation_info
    assert "model:" in inline_translation_info

    # Set Inline Translation Type to Dictionary and save
    page.open_inline_translation_editor()
    assert page.select_inline_translation_type("Dictionary") == "Dictionary"
    assert page.select_dictionary("Google Translator")

    browser.take_screenshot("Before Inline Translation type Dictionary Save")
    page.save_changes()

    inline_translation_info = page.get_inline_translation_info()
    assert "Type:" in inline_translation_info
    assert "GoogleTranslator" in inline_translation_info
    assert "Dictionary:" in inline_translation_info

    browser.take_screenshot("Final")
