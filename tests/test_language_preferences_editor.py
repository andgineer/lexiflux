import pytest
from django.urls import reverse
import allure
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from tests.conftest import USER_PASSWORD


@allure.epic('End-to-end (selenium)')
@allure.feature('Language Preferences')
@allure.story('Language Preferences Editor')
@pytest.mark.docker
@pytest.mark.selenium
@pytest.mark.django_db
def test_language_preferences_editor(browser, approved_user, caplog, client):
    browser.login(approved_user, USER_PASSWORD)

    # Navigate to the language preferences editor
    browser.goto(reverse('language-preferences'))

    # Wait for the page to load
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "language-selection-card"))
    )
    allure.attach(
        browser.get_screenshot_as_png(),
        name='language_preferences_initial',
        attachment_type=allure.attachment_type.PNG
    )
    # Check if the page title is correct
    assert "Language Tool Preferences" in browser.find_element(By.CLASS_NAME, "container-fluid").text

    # Test language selection (Note: This might need adjustment based on how your language selection is implemented)
    language_select = browser.find_element(By.CLASS_NAME, "language-select-wrapper")
    assert "English" in language_select.text  # Assuming English is the default language

    # Test inline translation settings
    try:
        inline_translation_edit = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "inline-translation-edit"))
        )
        inline_translation_edit.click()
    except TimeoutException:
        allure.attach(
            browser.get_screenshot_as_png(),
            name='edit_button_not_found',
            attachment_type=allure.attachment_type.PNG
        )
        raise

    # Wait for the modal to appear
    modal = WebDriverWait(browser, 10).until(
        EC.visibility_of_element_located((By.ID, "articleModal"))
    )

    # Test changing inline translation type
    try:
        type_select = WebDriverWait(modal, 10).until(
            EC.presence_of_element_located((By.ID, "article-type-select"))
        )
        select = Select(type_select)

        # Select "Dictionary" or a similar option
        try:
            select.select_by_visible_text("Translate")
        except NoSuchElementException:
            # If "Dictionary" is not available, select the first option that contains "Translate"
            dictionary_option = next((option for option in select.options if "Translate" in option.text), None)
            if dictionary_option:
                select.select_by_visible_text(dictionary_option.text)
            else:
                # If no option contains "Dictionary", select the first option
                select.select_by_index(0)
        print(f"Selected article type: {select.first_selected_option.text}")
    except TimeoutException:
        allure.attach(
            browser.get_screenshot_as_png(),
            name='type_select_not_found',
            attachment_type=allure.attachment_type.PNG
        )
        raise

    # Test selecting a dictionary (if applicable)
    try:
        dict_select = WebDriverWait(modal, 10).until(
            EC.presence_of_element_located((By.ID, "dictionary-select"))
        )
        select = Select(dict_select)

        # Try to select "GoogleTranslator" or a similar option
        try:
            select.select_by_visible_text("GoogleTranslator")
        except NoSuchElementException:
            # If "GoogleTranslator" is not available, select the first option
            select.select_by_index(0)
        print(f"Selected dictionary option: {select.first_selected_option.text}")
    except TimeoutException:
        allure.attach(
            browser.get_screenshot_as_png(),
            name='dict_select_not_found',
            attachment_type=allure.attachment_type.PNG
        )
        print("Dictionary select not found or not applicable for the selected article type")

    allure.attach(
        browser.get_screenshot_as_png(),
        name='language_preferences_editor_before_save',
        attachment_type=allure.attachment_type.PNG
    )

    # Save the changes
    try:
        save_button = WebDriverWait(modal, 10).until(
            EC.element_to_be_clickable((By.ID, "save-article-button"))
        )
        save_button.click()
    except TimeoutException:
        allure.attach(
            browser.get_screenshot_as_png(),
            name='save_button_not_found',
            attachment_type=allure.attachment_type.PNG
        )
        raise

    # Wait for the modal to close
    WebDriverWait(browser, 10).until(
        EC.invisibility_of_element_located((By.ID, "articleModal"))
    )

    # Verify the changes are reflected
    inline_translation_info = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "inline-translation-info"))
    )
    assert "Type:" in inline_translation_info.text
    assert "Translate" in inline_translation_info.text
    assert "model:" in inline_translation_info.text

    allure.attach(
        browser.get_screenshot_as_png(),
        name='language_preferences_editor_final',
        attachment_type=allure.attachment_type.PNG
    )
