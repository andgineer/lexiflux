import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tests.page_models.base_page import BasePage
from .selenium_utils import retry_on_stale_element


class LibraryPage(BasePage):
    @allure.step("Navigate to library page")
    def goto(self):
        self.browser.goto('/library')
        self.wait_for_page_load()

    def wait_for_page_load(self):
        self.wait_for_element((By.CLASS_NAME, "card"))

    def get_page_title(self):
        return self.browser.find_element(By.TAG_NAME, "h2").text

    @retry_on_stale_element()
    def get_first_book_info(self):
        books = self.browser.find_elements(By.CSS_SELECTOR, "table tbody tr")
        if books:
            title = books[0].find_element(By.CSS_SELECTOR, "td:first-child a").text
            author = books[0].find_element(By.CSS_SELECTOR, "td:nth-child(2)").text
            return title.strip(), author.strip()
        return None, None

    @retry_on_stale_element()
    def open_edit_modal_for_first_book(self):
        edit_buttons = self.browser.find_elements(By.CSS_SELECTOR, "table tbody tr .btn-outline-secondary")
        if edit_buttons:
            edit_buttons[0].click()
            self.wait_for_modal()

    def wait_for_modal(self):
        # Wait for modal to appear
        modal = WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.ID, "editBookModal"))
        )
        # Wait for modal animation to complete
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".modal.show"))
        )
        # Additional small delay to ensure modal is fully rendered
        self.browser.implicitly_wait(0.5)
        return modal

    @retry_on_stale_element()
    def get_edit_dialog_info(self):
        title_input = self.wait_for_element((By.ID, "bookTitle"))
        author_input = self.wait_for_element((By.ID, "bookAuthor"))
        return title_input.get_attribute("value"), author_input.get_attribute("value")

    @retry_on_stale_element()
    def edit_book_title(self, new_title):
        title_input = self.wait_for_element((By.ID, "bookTitle"))
        title_input.clear()
        self.browser.implicitly_wait(0.2)
        title_input.send_keys(new_title)

    @retry_on_stale_element()
    def edit_book_author(self, new_author):
        author_input = self.wait_for_element((By.ID, "bookAuthor"))
        author_input.clear()
        self.browser.implicitly_wait(0.2)
        author_input.send_keys(new_author)

    def save_book_changes(self):
        save_button = self.wait_for_clickable((By.CSS_SELECTOR, "#editBookModal .btn-primary"))
        save_button.click()

        # Wait for HTMX request to complete
        WebDriverWait(self.browser, 10).until(
            lambda driver: driver.execute_script("return !htmx.requesting")
        )

        # Wait for table to be updated
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )