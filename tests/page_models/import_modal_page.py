import time

import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from tests.page_models.base_page import BasePage
from tests.page_models.selenium_utils import retry_on_stale_element


class ImportModalPage(BasePage):
    @allure.step("Open import modal")
    def open_import_modal(self):
        """Click the Import Books button and wait for the modal to appear."""
        import_button = self.wait_for_clickable(
            (By.XPATH, "//button[contains(text(), 'Import Books')]")
        )
        import_button.click()
        self.wait_for_modal()
        self.browser.take_screenshot("Import Modal Open")
        assert "Import Book" == self.get_modal_title()

    def wait_for_modal(self):
        return WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "importModal"))
        )

    @allure.step("Waiting for import modal to close")
    def wait_for_modal_to_close(self):
        # Wait for modal to disappear
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((By.ID, "importModal"))
        )
        # Wait for the modal backdrop to disappear
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "modal-backdrop"))
        )

    def get_modal_title(self):
        return self.wait_for_element((By.ID, "importModalLabel")).text

    def select_file_tab(self):
        self.wait_for_clickable((By.ID, "file-tab")).click()
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "file-pane"))
        )

    def select_url_tab(self):
        self.wait_for_clickable((By.ID, "url-tab")).click()
        WebDriverWait(self.browser, 10).until(EC.visibility_of_element_located((By.ID, "url-pane")))

    def select_paste_tab(self):
        self.wait_for_clickable((By.ID, "paste-tab")).click()
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "paste-pane"))
        )

    @retry_on_stale_element()
    def upload_file(self, file_path):
        file_input = self.wait_for_element((By.ID, "bookFile"))
        file_input.send_keys(file_path)

    @retry_on_stale_element()
    def enter_url(self, url):
        url_input = self.wait_for_element((By.ID, "bookUrl"))
        url_input.clear()
        url_input.send_keys(url)

    @retry_on_stale_element()
    def select_cleaning_level(self, level):
        """Select a cleaning level: minimal, moderate, or aggressive"""
        select = Select(self.wait_for_element((By.ID, "cleaningLevel")))
        select.select_by_value(level)

    @retry_on_stale_element()
    def enter_paste_content(self, content):
        # Use JavaScript to directly focus the textarea instead of clicking the overlay
        self.browser.execute_script("document.getElementById('pasteContentInput').focus();")

        # Then enter the text in the textarea
        textarea = self.wait_for_element((By.ID, "pasteContentInput"))
        textarea.clear()
        textarea.send_keys(content)

        # Verify the status was updated
        WebDriverWait(self.browser, 10).until(
            lambda driver: "Text content ready"
            in driver.find_element(By.ID, "pasteContentStatus").text
        )

    @retry_on_stale_element()
    def select_paste_format(self, format_type):
        """Select a paste format: txt or html"""
        select = Select(self.wait_for_element((By.ID, "pasteFormat")))
        select.select_by_value(format_type)

    def submit_import(self):
        modal = self.wait_for_modal()
        submit_button = modal.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        # Wait for HTMX request to complete
        WebDriverWait(self.browser, 10).until(
            lambda driver: driver.execute_script("return !htmx.requesting")
        )

    def get_error_message(self):
        try:
            error = self.browser.find_element(By.CSS_SELECTOR, ".alert-danger")
            return error.text
        except:
            return None

    def wait_for_edit_book_modal(self):
        """Wait for edit book modal to appear after successful import."""
        # Wait for edit book modal to appear
        edit_modal = WebDriverWait(self.browser, 20).until(
            EC.visibility_of_element_located((By.ID, "editBookModal"))
        )

        # Wait for modal to be fully loaded
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#editBookModal.modal.show"))
        )

        # Give it a moment to stabilize
        self.browser.implicitly_wait(1)

        return edit_modal

    def fill_edit_book_form(self, title, author):
        """Fill in the edit book form."""
        edit_modal = self.wait_for_edit_book_modal()

        # Wait for title input to be interactive
        title_input = WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((By.ID, "bookTitle"))
        )

        # Clear and set title
        title_input.clear()
        self.browser.implicitly_wait(0.5)
        title_input.send_keys(title)

        # Wait for author input to be interactive
        author_input = WebDriverWait(self.browser, 10).until(
            EC.element_to_be_clickable((By.ID, "bookAuthor"))
        )

        # Clear and set author
        author_input.clear()
        self.browser.implicitly_wait(0.5)
        author_input.send_keys(author)

        return edit_modal

    def save_book_changes(self):
        """Save changes in the edit book modal."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                edit_modal = self.wait_for_edit_book_modal()

                # Find and click the save button
                save_button = WebDriverWait(self.browser, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#editBookModal .btn-primary"))
                )

                # Use JavaScript to click the button (more reliable across browsers)
                self.browser.execute_script("arguments[0].click();", save_button)

                # Wait for HTMX request to complete
                WebDriverWait(self.browser, 10).until(
                    lambda driver: driver.execute_script("return !htmx.requesting")
                )

                # Wait for the modal to close
                WebDriverWait(self.browser, 10).until(
                    EC.invisibility_of_element_located((By.ID, "editBookModal"))
                )

                # Wait for the modal backdrop to disappear
                WebDriverWait(self.browser, 10).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "modal-backdrop"))
                )
                # Success, break out of retry loop
                break

            except Exception:
                if attempt == max_attempts - 1:  # Last attempt
                    raise  # Re-raise the exception if all attempts failed
                time.sleep(1)  # Wait before retrying
