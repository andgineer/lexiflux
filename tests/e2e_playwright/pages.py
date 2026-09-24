import re

from django.urls import reverse
from playwright.sync_api import Locator, Page, expect


class ReaderPage:
    def __init__(self, page: Page, server_url: str) -> None:
        self.page = page
        self.server_url = server_url

    def open(self, book_code: str) -> "ReaderPage":
        self.page.goto(f"{self.server_url}{reverse('reader')}?book-code={book_code}")
        expect(self.page.locator("#words-container span.word").first).to_be_visible()
        return self

    def open_sidebar(self) -> None:
        sidebar = self.page.locator("#lexical-panel")
        if "show" not in (sidebar.get_attribute("class") or "").split():
            self.page.locator("#lexical-panel-button").click()
        expect(sidebar).to_have_class(_has_class("show"))

    def word(self, text: str) -> Locator:
        return self.page.locator("#words-container span.word", has_text=text).first

    def click_word(self, text: str) -> None:
        self.word(text).click()

    def panel(self, number: int = 1) -> Locator:
        return self.page.locator(f"#lexical-content-{number}")

    def inline_translation(self) -> Locator:
        return self.page.locator("span.translation-span .translation-text").first


def _has_class(name: str) -> re.Pattern[str]:
    return re.compile(rf"(^|\s){re.escape(name)}(\s|$)")
