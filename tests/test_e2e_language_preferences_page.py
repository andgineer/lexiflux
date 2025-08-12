import pytest
import allure
from django.urls import reverse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from lexiflux.models import Language, LanguagePreferences
from tests.conftest import USER_PASSWORD
from tests.page_models.language_preferences_page import LanguagePreferencesPage


@allure.epic("End-to-end (selenium)")
@allure.feature("Library Page")
@allure.story("Un-approved user cannot access library page")
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_library_page_upapproved_user_cannot_access(browser, user):
    browser.login(user, USER_PASSWORD, wait_view=None)
    WebDriverWait(browser, 3).until(
        EC.url_to_be(browser.host + reverse("login")),  # raise TimeoutException if not
        message="Expected to be redirected to login page again after login with unapproved user.",
    )
    assert "Your account is not approved yet." in browser.errors_text

    # just to be sure
    allure.attach(
        browser.get_screenshot_as_png(),
        name="after_unapproved_login_screenshot",
        attachment_type=allure.attachment_type.PNG,
    )


@allure.epic("End-to-end (selenium)")
@allure.feature("Language Preferences Page")
@allure.story("Inline Translation Editor")
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_language_preferences_page_inline_translation(browser, user_preferences):
    with allure.step("Login and navigate to language preferences"):
        browser.login(user_preferences, USER_PASSWORD)
        page = LanguagePreferencesPage(browser)
        page.goto()
        # assert page.wait_for_options(), "Failed to load models/dictionaries options after multiple attempts"
        browser.take_screenshot("Initial")

    with allure.step("Verify initial page state"):
        assert "Dictionary & AI Insights Settings" in page.get_page_title()
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


@allure.epic("End-to-end (selenium)")
@allure.feature("Language Preferences Page")
@allure.story("Global Preferences")
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_e2e_language_preferences_global_settings(browser, user_preferences):
    # Create second language preference to make initial state non-global
    spanish = Language.objects.get(google_code="es")
    LanguagePreferences.get_or_create_language_preferences(user_preferences, spanish)

    with allure.step("Login and navigate to language preferences"):
        browser.login(user_preferences, USER_PASSWORD)
        page = LanguagePreferencesPage(browser)
        page.goto()
        browser.take_screenshot("Initial state")

    with allure.step("Verify initial non-global state"):
        assert user_preferences.language_preferences.count() > 1, (
            "Should have multiple language preferences"
        )

    with allure.step("Open global preferences confirmation modal"):
        page.set_global_preferences()
        modal = WebDriverWait(browser, 10).until(
            EC.visibility_of_element_located((By.ID, "globalPreferencesConfirmModal"))
        )
        assert "Apply to all languages" in modal.text

        apply_button = modal.find_element(By.XPATH, ".//button[contains(text(), 'Apply to all')]")
        apply_button.click()
        WebDriverWait(browser, 10).until(
            EC.invisibility_of_element_located((By.ID, "globalPreferencesConfirmModal"))
        )

    with allure.step("Verify language preferences became global"):
        assert user_preferences.language_preferences.count() == 1, (
            "Should have only one language preference"
        )
