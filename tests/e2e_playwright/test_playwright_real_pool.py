import os
import time
from unittest.mock import patch

import pytest
from playwright.sync_api import Page

from lexiflux.language.broker import get_broker as real_get_broker
from lexiflux.language.broker import llms_for as real_llms_for
from tests.e2e_playwright.pages import ReaderPage

FIRST_TEXT_SECONDS = 3
ANSWER_TIMEOUT_MS = 40_000

pytestmark = [
    pytest.mark.real_llm,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        os.environ.get("LEXIFLUX_REAL_LLM") != "1",
        reason="calls the real free pool; set LEXIFLUX_REAL_LLM=1",
    ),
]


def test_free_pool_article_streams_in_the_browser(
    logged_in_page: Page, server_url, book, language_preferences
):
    article = language_preferences.get_lexical_articles()[0]
    # Free pool only: a paid model here would spend the operator's money.
    assert (article.type, article.parameters["model"]) == ("AI dictionary", "pool")

    with (
        patch("lexiflux.language.llm.llms_for", real_llms_for),
        patch("lexiflux.language.broker.get_broker", real_get_broker),
    ):
        real_get_broker()
        reader = ReaderPage(logged_in_page, server_url).open(book.code)
        reader.open_sidebar()
        panel = reader.panel(1)

        started = time.monotonic()
        reader.click_word("page")
        panel.page.wait_for_function(
            """el => !el.querySelector('.lexical-status') && el.textContent.trim().length > 0""",
            arg=panel.element_handle(),
            timeout=ANSWER_TIMEOUT_MS,
        )
        first_text_seconds = time.monotonic() - started
        alert = panel.locator(".alert")
        assert alert.count() == 0, f"the pool answered with an error: {alert.first.inner_text()}"
        print(f"first text after {first_text_seconds:.2f} s: {panel.inner_text()[:80]!r}")
        assert first_text_seconds < FIRST_TEXT_SECONDS
