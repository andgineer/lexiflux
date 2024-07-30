import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tests.page_models.base_page import BasePage

class LibraryPage(BasePage):
    @allure.step("Navigate to library page")
    def goto(self):
        self.browser.goto('/library')  # Adjust the URL as needed
        self.wait_for_page_load()

    def wait_for_page_load(self):
        self.wait_for_element((By.CLASS_NAME, "card"))

    def get_page_title(self):
        return self.browser.find_element(By.TAG_NAME, "h2").text

    def get_first_book_info(self):
        books = self.browser.find_elements(By.CLASS_NAME, "list-group-item")
        if books:
            full_text = books[0].find_element(By.TAG_NAME, "a").text
            parts = full_text.split(" by ", 1)
            title = parts[0].strip()
            author = parts[1].strip() if len(parts) > 1 else ""
            return title, author
        return None, None

    def open_edit_modal_for_first_book(self):
        edit_buttons = self.browser.find_elements(By.CSS_SELECTOR, ".list-group-item .btn-secondary")
        if edit_buttons:
            edit_buttons[0].click()
            self.wait_for_modal()

    def wait_for_modal(self):
        return WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "editBookModal"))
        )

    def get_edit_dialog_info(self):
        title_input = self.wait_for_element((By.ID, "bookTitle"))
        author_input = self.wait_for_element((By.ID, "bookAuthor"))
        return title_input.get_attribute("value"), author_input.get_attribute("value")

    def edit_book_title(self, new_title):
        title_input = self.wait_for_element((By.ID, "bookTitle"))
        title_input.clear()
        title_input.send_keys(new_title)

    def edit_book_author(self, new_title):
        author_input = self.wait_for_element((By.ID, "bookAuthor"))
        author_input.clear()
        author_input.send_keys(new_title)

    def save_book_changes(self):
        save_button = self.wait_for_clickable((By.CSS_SELECTOR, "#editBookModal .btn-primary"))
        save_button.click()
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((By.ID, "editBookModal"))
        )
        # Wait for the modal backdrop to disappear
        WebDriverWait(self.browser, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "modal-backdrop"))
        )