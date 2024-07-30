import pytest
import allure
from tests.conftest import USER_PASSWORD
from tests.page_models.language_preferences_page import LanguagePreferencesPage


@allure.epic('End-to-end (selenium)')
@allure.feature('Language Preferences Page')
@allure.story('Inline Translation Editor')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_language_preferences_page_inline_translation(browser, approved_user):
    with allure.step("Login and navigate to language preferences"):
        browser.login(approved_user, USER_PASSWORD)
        page = LanguagePreferencesPage(browser)
        page.goto()
        # assert page.wait_for_options(), "Failed to load models/dictionaries options after multiple attempts"
        browser.take_screenshot("Initial")

    with allure.step("Verify initial page state"):
        assert "Language Preferences" in page.get_page_title()
        assert "English" in page.get_selected_language()

    with allure.step("Open and configure Translate in inline translation"):
        page.open_inline_translation_editor()
        assert page.select_inline_translation_type("Translate") == "Translate"
        page.select_model()
        browser.take_screenshot("Before Inline Translation type Translation Save")
        page.save_changes()

        inline_translation_info = page.get_inline_translation_info()
        assert "Type:" in inline_translation_info
        assert "Translate" in inline_translation_info
        assert "model:" in inline_translation_info

    with allure.step("Open and configure Dictionary in inline translation"):
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
