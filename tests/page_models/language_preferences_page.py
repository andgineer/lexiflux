from typing import Optional

from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

class LanguagePreferencesPage:
    def __init__(self, browser):
        self.browser = browser

    def wait_for_page_load(self):
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "language-selection-card"))
        )

    def get_page_title(self):
        return self.browser.find_element(By.CLASS_NAME, "container-fluid").text

    def get_selected_language(self):
        language_select = self.browser.find_element(By.CLASS_NAME, "language-select-wrapper")
        return language_select.text

    def open_inline_translation_editor(self):
        edit_button = WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((By.ID, "inline-translation-edit"))
        )
        edit_button.click()

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