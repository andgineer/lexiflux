from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tests.page_models.base_page import BasePage


class ReaderPage(BasePage):
    WORDS_CONTAINER = (By.ID, "words-container")
    WORD_SPAN = (By.CSS_SELECTOR, "span.word")
    TRANSLATION_SPAN = (By.CSS_SELECTOR, "span.translation-span")

    def __init__(self, browser):
        super().__init__(browser)

    def wait_for_page_load(self):
        return self.wait_for_element(self.WORDS_CONTAINER)

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