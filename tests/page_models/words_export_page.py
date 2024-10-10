import time
from datetime import datetime

from selenium.common import StaleElementReferenceException, NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from tests.page_models.base_page import BasePage

class WordsExportPage(BasePage):
    def __init__(self, browser):
        super().__init__(browser)
        self.url = self.browser.host + '/words-export/'

    def goto(self):
        self.browser.get(self.url)

    def get_error_message(self):
        return self.wait_for_element((By.CLASS_NAME, 'alert-danger')).text

    def is_error_message_present(self):
        try:
            self.wait_for_element((By.CLASS_NAME, 'alert-danger'), timeout=1)
            return True
        except:
            return False

    def wait_for_success_message(self, expected_message, timeout=10):
        try:
            element = self.wait_for_element((By.CLASS_NAME, 'alert-success'))
            return element.text if element else None
        except:
            return None

    def get_success_message(self):
        return self.wait_for_element((By.CLASS_NAME, 'alert-success')).text

    def is_form_controls_visible(self):
        try:
            form_control = self.wait_for_element((By.ID, 'languageSelect'), timeout=3)
            return form_control.is_displayed()
        except:
            return False

    def select_language(self, language_name):
        select = Select(self.wait_for_element((By.ID, 'languageSelect')))
        select.select_by_visible_text(language_name)

    def get_selected_language(self):
        select = Select(self.wait_for_element((By.ID, 'languageSelect')))
        return select.first_selected_option.text

    def set_min_datetime(self, datetime_value):
        min_datetime_input = self.wait_for_element((By.ID, 'minDateTime'))
        min_datetime_input.clear()
        min_datetime_input.send_keys(datetime_value)

    def get_min_datetime(self):
        return self.wait_for_element((By.ID, 'minDateTime')).get_attribute('value')

    def set_deck_name(self, deck_name):
        deck_name_input = self.wait_for_element((By.ID, 'deck-name'))
        deck_name_input.clear()
        deck_name_input.send_keys(deck_name)

    def get_deck_name(self):
        return self.wait_for_element((By.ID, 'deckName')).get_attribute('value')

    def select_export_method(self, method):
        method_radio = self.wait_for_element((By.CSS_SELECTOR, f'input[type="radio"][value="{method}"]'))
        method_radio.click()

    def get_selected_export_method(self):
        return self.wait_for_element((By.CSS_SELECTOR, 'input[type="radio"]:checked')).get_attribute('value')

    def click_export_button(self):
        export_button = self.wait_for_clickable((By.ID, 'export-button'))
        export_button.click()

    def wait_for_export_button_disabled(self, timeout=60):
        start_time = time.time()
        poll_interval = 0.5  # Check every half second

        while time.time() - start_time < timeout:
            try:
                if self.is_export_button_disabled():
                    print("Export button became disabled")
                    return True

            except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
                print(f"{datetime.now().isoformat()} - Exception while checking button: {str(e)}")

            time.sleep(poll_interval)

        print(f"{datetime.now().isoformat()} - Timeout reached. Button did not become disabled.")
        return False

    def is_export_button_disabled(self):
        try:
            export_button = self.wait_for_element((By.ID, 'export-button'), timeout=5)

            button_text = export_button.text.strip().lower()
            if "no words to export" in button_text:
                print("Detected button text: No words to export")
                return True

            print(
                f"is_enabled: {export_button.is_enabled()}, "
                f"disabled: {export_button.get_attribute('disabled')}, "
                f"class: {export_button.get_attribute('class')}"
            )
            return (
                not export_button.is_enabled()
                or export_button.get_attribute('disabled') is not None
                or 'disabled' in export_button.get_attribute('class')
            )
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            return False

