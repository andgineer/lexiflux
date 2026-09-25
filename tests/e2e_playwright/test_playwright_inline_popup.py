import gzip
import threading
import time
from collections.abc import Iterator
from functools import partial
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from django.conf import settings
from playwright.sync_api import expect

from lexiflux.language.llm import INLINE_TRANSLATION_SECONDS
from lexiflux.language.translation import AVAILABLE_TRANSLATORS, GoogleTranslator, get_translator
from lexiflux.language.wiktionary import LICENSE_URL
from lexiflux.language.wiktionary_import import SOURCES, ImportReport, build
from lexiflux.models import Book, BookPage, Language, LanguagePreferences
from tests.e2e_playwright.fakes import FakePool
from tests.e2e_playwright.pages import ReaderPage

pytestmark = pytest.mark.django_db(transaction=True)

WIKTIONARY_FIXTURES = Path(__file__).parent.parent / "resources" / "wiktionary"
TEXT = (
    "The old armchair had seen better days. When Tom sat down, two springs creaked deep "
    "inside the seat. He jumped up at once."
)
SPRING_ALTERNATIVES = [
    [["пружины", "springs", None, None, 10]],
    [
        ["noun", ["пружина", "весна", "источник"], [], "spring", 1],
        ["verb", ["возникать"], [], "spring", 2],
    ],
    "en",
]
ALERT_MARGIN_SECONDS = 2.5


@pytest.fixture
def fake_translator() -> None:
    # Overrides the conftest's autouse fake: these tests run the real popup translators.
    return


@pytest.fixture(autouse=True)
def fresh_translators() -> Iterator[None]:
    # get_translator keeps its translators across tests; a kept Google one has a real transport.
    get_translator.cache_clear()
    yield
    get_translator.cache_clear()


@pytest.fixture
def fake_pool() -> Iterator[FakePool]:
    pool = FakePool(answer="пружина")
    with patch("lexiflux.language.llm.llms_for", return_value=pool):
        yield pool
        # Release the daemon thread a stalled call left waiting.
        if pool.stall is not None:
            pool.stall.set()


@pytest.fixture
def book(approved_user, author) -> Book:
    # Not the shared book: the reader caches page HTML by book code, and other tests cache
    # another text under that book's code.
    book = Book.objects.create(
        title="The Old Armchair",
        author=author,
        language=Language.objects.get(name="English"),
        code="the-old-armchair",
        owner=approved_user,
    )
    BookPage.objects.create(book=book, number=1, content=TEXT)
    return book


@pytest.fixture
def russian_reader(language_preferences: LanguagePreferences) -> LanguagePreferences:
    language_preferences.user_language = Language.objects.get(name="Russian")
    language_preferences.save()
    return language_preferences


def _use(preferences: LanguagePreferences, dictionary: str) -> None:
    preferences.inline_translation_type = "Dictionary"
    preferences.inline_translation_parameters = {"dictionary": dictionary}
    preferences.save()


def _open(logged_in_page, server_url, book) -> ReaderPage:
    return ReaderPage(logged_in_page, server_url).open(book.code)


def test_popup_shows_the_llm_translation_by_default(
    logged_in_page, server_url, book, russian_reader, fake_pool
):
    assert russian_reader.inline_translation_parameters == {"dictionary": "LLMTranslation"}
    reader = _open(logged_in_page, server_url, book)

    reader.click_word("springs")

    expect(reader.inline_translation()).to_have_text("пружина")
    (prompt,) = fake_pool.prompts
    assert "into Russian" in prompt
    assert "two ⟦springs⟧ creaked" in prompt
    assert "better days." in prompt and "He jumped up at once." in prompt


def test_popup_shows_the_busy_alert_when_the_pool_stalls(
    logged_in_page, server_url, book, russian_reader, fake_pool
):
    fake_pool.stall = threading.Event()
    reader = _open(logged_in_page, server_url, book)

    started = time.monotonic()
    reader.click_word("springs")
    alert = reader.inline_translation().locator(".alert.alert-info")
    expect(alert).to_have_text(
        "The AI models are busy right now. Please retry.",
        timeout=(INLINE_TRANSLATION_SECONDS + ALERT_MARGIN_SECONDS) * 1000,
    )
    elapsed = time.monotonic() - started

    assert INLINE_TRANSLATION_SECONDS <= elapsed < INLINE_TRANSLATION_SECONDS + ALERT_MARGIN_SECONDS
    expect(reader.inline_translation()).not_to_contain_text("пружина")


@pytest.fixture
def wiktionary_data(tmp_path) -> Iterator[Path]:
    downloads = []
    for source in SOURCES:
        path = tmp_path / source.file_name
        path.write_bytes(
            gzip.compress((WIKTIONARY_FIXTURES / source.file_name.removesuffix(".gz")).read_bytes())
        )
        downloads.append((source, path))
    target = tmp_path / "wiktionary.sqlite3"
    build(target, downloads, frozenset({"ru"}), ImportReport(), progress=lambda _message: None)
    with patch.object(settings, "WIKTIONARY_DATABASE", target):
        yield target


def test_popup_shows_the_wiktionary_senses_with_attribution(
    logged_in_page, server_url, book, russian_reader, wiktionary_data
):
    _use(russian_reader, "Wiktionary")
    reader = _open(logged_in_page, server_url, book)

    reader.click_word("springs")

    popup = reader.inline_translation()
    entry = popup.locator(".wiktionary-entry").first
    expect(entry.locator(".wiktionary-word")).to_have_text("spring")
    expect(entry.locator(".wiktionary-pos")).to_have_text("noun")
    expect(entry.locator(".wiktionary-senses li")).to_have_text(["весна", "пружина, рессора"])
    attribution = popup.locator(".wiktionary-attribution")
    expect(attribution).to_have_text("from Wiktionary, CC BY-SA 4.0")
    expect(attribution.get_by_role("link", name="Wiktionary")).to_have_attribute(
        "href", "https://ru.wiktionary.org/wiki/spring"
    )
    expect(attribution.get_by_role("link", name="CC BY-SA 4.0")).to_have_attribute(
        "href", LICENSE_URL
    )
    expect(popup.locator(".wiktionary")).to_have_css("text-align", "left")


def test_wiktionary_attribution_stays_in_view_below_a_long_sense_list(
    logged_in_page, server_url, book, russian_reader, wiktionary_data
):
    _use(russian_reader, "Wiktionary")
    reader = _open(logged_in_page, server_url, book)
    reader.click_word("springs")
    popup = reader.inline_translation()
    expect(popup.locator(".wiktionary-attribution")).to_be_visible()

    popup.locator(".wiktionary-senses").first.evaluate(
        "list => list.insertAdjacentHTML('beforeend', '<li>sense</li>'.repeat(40))"
    )

    expect(popup.locator(".wiktionary-senses li").last).not_to_be_in_viewport()
    expect(popup.locator(".wiktionary-attribution")).to_be_in_viewport()


class GoogleEndpoint:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json=SPRING_ALTERNATIVES)


def test_popup_shows_google_alternatives(logged_in_page, server_url, book, russian_reader):
    endpoint = GoogleEndpoint()
    google = partial(GoogleTranslator, transport=httpx.MockTransport(endpoint.handle))
    _use(russian_reader, "Google")

    with patch.dict(AVAILABLE_TRANSLATORS, {"Google": (google, "Google")}):
        reader = _open(logged_in_page, server_url, book)
        reader.click_word("springs")

        popup = reader.inline_translation()
        expect(popup).to_contain_text("пружины")
        expect(popup.locator("i")).to_have_text(["noun:", "verb:"])
        expect(popup).to_contain_text("noun: пружина, весна, источник")
        expect(popup).to_contain_text("verb: возникать")
    (request,) = endpoint.requests
    assert request.url.params["client"] == "dict-chrome-ex"
    assert request.url.params.get_list("dt") == ["t", "bd"]
    assert (request.url.params["sl"], request.url.params["tl"]) == ("en", "ru")
