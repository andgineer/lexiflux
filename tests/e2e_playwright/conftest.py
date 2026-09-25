import os
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
from django.conf import settings
from django.test import Client
from playwright.sync_api import Page

from lexiflux.models import LanguagePreferences
from tests.e2e_playwright.fakes import FakeArticleStream
from tests.e2e_playwright.pages import ReaderPage

# Playwright's sync API keeps an event loop in the main thread, which trips Django's
# async-safety check on every ORM call the tests make.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

HERE = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # Called with the whole session's items, not only this folder's.
    for item in items:
        if HERE in item.path.parents:
            item.add_marker(pytest.mark.playwright)


@pytest.fixture(scope="session")
def browser(launch_browser):
    # The root conftest's Selenium `browser` fixture would shadow pytest-playwright's.
    playwright_browser = launch_browser()
    yield playwright_browser
    playwright_browser.close()


@pytest.fixture
def fake_stream() -> Iterator[FakeArticleStream]:
    fake = FakeArticleStream()
    with patch("lexiflux.views.lexical_views.stream_article", side_effect=fake):
        yield fake
        # A gate left closed would hold the single-threaded live server for the next test.
        fake.release_all()


@pytest.fixture(autouse=True)
def fake_translator() -> Iterator[MagicMock]:
    translator = MagicMock()
    translator.translate.side_effect = lambda term: f"Translation of {term.word}"
    with patch("lexiflux.views.lexical_views.get_translator", return_value=translator):
        yield translator


@pytest.fixture
def server_url(live_server) -> str:
    # The live server binds 0.0.0.0 for the Selenium hub; the local browser talks to localhost.
    return f"http://localhost:{urlparse(live_server.url).port}"


@pytest.fixture
def page_errors(page: Page) -> Iterator[list[str]]:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield errors
    assert not errors, f"JavaScript errors on the page: {errors}"


@pytest.fixture
def logged_in_page(page: Page, server_url: str, approved_user, page_errors) -> Page:
    client = Client()
    client.force_login(approved_user)
    page.context.add_cookies(
        [
            {
                "name": settings.SESSION_COOKIE_NAME,
                "value": client.cookies[settings.SESSION_COOKIE_NAME].value,
                "url": server_url,
            }
        ]
    )
    return page


@pytest.fixture
def reader(logged_in_page: Page, server_url: str, book) -> ReaderPage:
    return ReaderPage(logged_in_page, server_url).open(book.code)


@pytest.fixture
def language_preferences(approved_user, book) -> LanguagePreferences:
    return LanguagePreferences.get_or_create_language_preferences(approved_user, book.language)
