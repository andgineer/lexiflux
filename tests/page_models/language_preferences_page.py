from typing import Optional

import allure
from django.urls import reverse
from selenium.common import TimeoutException, NoSuchElementException, NoAlertPresentException, \
    UnexpectedAlertPresentException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

class LanguagePreferencesPage:
    def __init__(self, browser):
        self.browser = browser

    def wait_for_page_load(self):
        try:
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "language-selection-card"))
            )
        except TimeoutException as e:
            alert_text = self.check_for_alert()
            if alert_text:
                raise AssertionError(f"Unexpected alert during page load: {alert_text}") from e
            raise

    def check_for_alert(self):
        try:
            WebDriverWait(self.browser, 3).until(EC.alert_is_present())
            alert = self.browser.switch_to.alert
            alert_text = alert.text
            allure.attach(alert_text, name="Unexpected Alert", attachment_type=allure.attachment_type.TEXT)
            return alert_text
        except (TimeoutException, NoAlertPresentException):
            return None

    @allure.step("Navigate to language preferences page")
    def goto(self):
        self.browser.goto(reverse('language-preferences'))
        self.wait_for_page_load()

    def get_page_title(self):
        return self.browser.find_element(By.CLASS_NAME, "container-fluid").text

    def get_selected_language(self):
        language_select = self.browser.find_element(By.CLASS_NAME, "language-select-wrapper")
        return language_select.text

    def open_inline_translation_editor(self):
        try:
            WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.ID, "inline-translation-edit"))
            ).click()
        except UnexpectedAlertPresentException as e:
            alert_text = self.check_for_alert()
            if alert_text:
                raise AssertionError(f"Unexpected alert when opening editor: {alert_text}") from e
            raise

    def wait_for_modal(self):
        return WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "articleModal"))
        )

    def select_inline_translation_type(self, type_text):
        modal = self.wait_for_modal()
        type_select = WebDriverWait(modal, 10).until(
            EC.presence_of_element_located((By.ID, "article-type-select"))
        )
        select = Select(type_select)
        try:
            select.select_by_visible_text(type_text)
        except NoSuchElementException:
            options = [option for option in select.options if type_text in option.text]
            if options:
                select.select_by_visible_text(options[0].text)
            else:
                select.select_by_index(0)
        return select.first_selected_option.text

    def select_dictionary(self, name: Optional[str] = None):
        return self.select_option("dictionary-select", name)

    def select_model(self, name: Optional[str] = None):
        return self.select_option("model-select", name)

    def select_option(self, selector_id: str, option: Optional[str] = None):
        """Select an option from a select element by its visible text.

        name: The visible text of the option to select.
        """
        modal = self.wait_for_modal()
        try:
            dict_select = WebDriverWait(modal, 10).until(
                EC.presence_of_element_located((By.ID, selector_id))
            )
            select = Select(dict_select)
            if option is None:
                select.select_by_index(0)
            else:
                select.select_by_visible_text(option)
            return select.first_selected_option.text
        except TimeoutException:
            return None

    def save_changes(self):
        modal = self.wait_for_modal()
        save_button = WebDriverWait(modal, 10).until(
            EC.element_to_be_clickable((By.ID, "save-article-button"))
        )
        save_button.click()
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((By.ID, "articleModal"))
        )

        # Wait for the modal backdrop to disappear
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "modal-backdrop"))
        )

        # Additional check to ensure the page is interactive
        WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((By.ID, "inline-translation-edit"))
        )

    def get_inline_translation_info(self):
        info = WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.ID, "inline-translation-info"))
        )
        return info.text