import pytest
import allure
from django.urls import reverse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tests.conftest import USER_PASSWORD
from tests.page_models.language_preferences_page import LanguagePreferencesPage


@allure.epic('End-to-end (selenium)')
@allure.feature('Library Page')
@allure.story('Un-approved user cannot access library page')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_library_page_upapproved_user_cannot_access(browser, user):
    browser.login(user, USER_PASSWORD, wait_view=None)
    WebDriverWait(browser, 3).until(
        EC.url_to_be(browser.host + reverse('login')),  # raise TimeoutException if not
        message="Expected to be redirected to login page again after login with unapproved user.",
    )
    assert "Your account is not approved yet." in browser.errors_text

    # just to be sure
    allure.attach(
        browser.get_screenshot_as_png(),
        name='after_unapproved_login_screenshot',
        attachment_type=allure.attachment_type.PNG
    )


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
