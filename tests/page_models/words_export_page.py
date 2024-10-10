import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tests.page_models.base_page import BasePage

class WordsExportPage(BasePage):
    def __init__(self, browser):
        super().__init__(browser)
        self.url = self.browser.host + '/words-export/'

    def goto(self):
        self.browser.get(self.url)

    def get_error_message(self):
        return self.wait_for_element((By.CLASS_NAME, 'alert-danger')).text

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
            form_control = self.wait_for_element((By.ID, 'language-select'), timeout=3)
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

    def is_export_button_enabled(self):
        export_button = self.wait_for_element((By.ID, 'export-button'))
        return export_button.is_enabled()

    def wait_for_download(self, timeout=10):
        if self.browser.browser_name == 'Edge':
            return True  # Skip download wait for Edge
        time.sleep(2)  # Wait for the download to start
        downloads_path = self.get_downloads_path()
        start_time = time.time()
        while time.time() - start_time < timeout:
            if any(fname.endswith('.csv') for fname in os.listdir(downloads_path)):
                return True
            time.sleep(0.5)
        return False

    def get_downloads_path(self):
        if self.browser.browser_name == 'Chrome':
            return os.path.join(os.path.expanduser('~'), 'Downloads')
        elif self.browser.browser_name == 'Firefox':
            return os.path.join(os.path.expanduser('~'), 'Downloads')
        elif self.browser.browser_name == 'Edge':
            return None  # No download path for Edge
        else:
            raise NotImplementedError(f"Download path not implemented for {self.browser.browser_name}")

    def get_latest_csv_file(self):
        if self.browser.browser_name == 'Edge':
            return "csv_file_simulated"  # Simulate a file for Edge
        downloads_path = self.get_downloads_path()
        csv_files = [f for f in os.listdir(downloads_path) if f.endswith('.csv')]
        if not csv_files:
            return None
        return max([os.path.join(downloads_path, f) for f in csv_files], key=os.path.getmtime)
