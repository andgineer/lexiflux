# tests/page_models/reader_page.py

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tests.page_models.base_page import BasePage


class ReaderPage(BasePage):
    WORDS_CONTAINER = (By.ID, "words-container")
    WORD_SPAN = (By.CSS_SELECTOR, "span.word")
    TRANSLATION_SPAN = (By.CSS_SELECTOR, "span.translation-span")
    SIDEBAR_TABS = (By.CSS_SELECTOR, "#lexicalPanelTabs button.nav-link")
    SIDEBAR_BUTTON = (By.ID, "lexical-panel-button")
    SIDEBAR = (By.ID, "lexical-panel")
    MENU_ITEMS = (By.CSS_SELECTOR, "#dropdownMenuButton1 + .dropdown-menu .dropdown-item")

    def __init__(self, browser):
        super().__init__(browser)

    def wait_for_page_load(self, timeout=20):
        # Wait for the words container to be present
        words_container = self.wait_for_element(self.WORDS_CONTAINER, timeout)

        # Now wait for the content to actually be loaded
        WebDriverWait(self.browser, timeout).until(
            lambda driver: len(words_container.text.strip()) > 0,
            message="Content did not load within the specified time",
        )
        return words_container

    def get_page_content(self):
        words_container = self.wait_for_page_load()
        return words_container.text

    def click_word(self, word_text):
        words = self.browser.find_elements(*self.WORD_SPAN)
        for word in words:
            if word.text == word_text:
                word.click()
                break

    def get_translation(self):
        translation_span = self.wait_for_element(self.TRANSLATION_SPAN)
        return translation_span.text

    def wait_for_translation(self):
        return WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located(self.TRANSLATION_SPAN)
        )

    def sidebar_tab_titles(self):
        return [
            tab.get_attribute("textContent").strip()
            for tab in self.browser.find_elements(*self.SIDEBAR_TABS)
        ]

    def menu_item_titles(self):
        return [
            item.get_attribute("textContent").strip()
            for item in self.browser.find_elements(*self.MENU_ITEMS)
        ]

    def open_sidebar(self, timeout=10):
        sidebar = self.browser.find_element(*self.SIDEBAR)
        if "show" not in (sidebar.get_attribute("class") or "").split():
            self.wait_for_clickable(self.SIDEBAR_BUTTON, timeout).click()
        WebDriverWait(self.browser, timeout).until(
            lambda driver: "show" in (sidebar.get_attribute("class") or "").split(),
            message="Sidebar did not open",
        )

    def switch_sidebar_tab(self, number):
        self.wait_for_clickable((By.ID, f"lexical-tab-{number}")).click()

    def wait_for_article(self, number, text, timeout=10):
        content = (By.ID, f"lexical-content-{number}")
        WebDriverWait(self.browser, timeout).until(
            lambda driver: text in driver.find_element(*content).text,
            message=f"Article {number} did not show {text!r}",
        )
        return self.browser.find_element(*content)
