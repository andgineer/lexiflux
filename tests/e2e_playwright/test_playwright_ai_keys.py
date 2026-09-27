import pytest
from django.conf import settings
from django.urls import reverse
from llmbroker import NoLLMAvailableError
from playwright.sync_api import Page, expect

from lexiflux.language import key_store
from lexiflux.language.llm import ArticleEvent, article_error
from tests.e2e_playwright.pages import ReaderPage

pytestmark = pytest.mark.django_db(transaction=True)

OWN_KEY = "sk-playwright-own-key-9f3c"


def key_row(page: Page, ref: str):
    return page.locator(f'li.ai-key[data-ref="{ref}"]')


def test_save_and_clear_a_key(logged_in_page: Page, server_url, approved_user, server_keys):
    server_keys("GROQ_API_KEY", "gsk-server-key-never-shown")
    page = logged_in_page
    page.goto(f"{server_url}{reverse('ai-keys')}")
    groq, openai = key_row(page, "GROQ_API_KEY"), key_row(page, "OPENAI_API_KEY")
    expect(groq.locator(".key-source")).to_have_text("Server's key")
    expect(groq.locator(".key-hint a")).to_have_attribute("target", "_blank")
    expect(openai.locator(".key-source")).to_have_text("Not set")
    expect(openai.locator(".key-save")).to_be_disabled()
    expect(openai.locator(".key-clear")).to_be_disabled()

    openai.locator(".key-input").fill(OWN_KEY)
    openai.locator(".key-save").click()

    expect(openai.locator(".key-source")).to_have_text(f"Your key …{OWN_KEY[-4:]}")
    expect(openai.locator(".key-input")).to_have_value("")
    assert key_store.own_key(approved_user.id, "OPENAI_API_KEY") == OWN_KEY
    page.reload()
    expect(openai.locator(".key-source")).to_have_text(f"Your key …{OWN_KEY[-4:]}")
    assert OWN_KEY not in page.content()
    assert "gsk-server-key-never-shown" not in page.content()

    openai.locator(".key-clear").click()

    expect(openai.locator(".key-source")).to_have_text("Not set")
    expect(openai.locator(".key-clear")).to_be_disabled()
    assert key_store.own_key(approved_user.id, "OPENAI_API_KEY") is None


def test_a_short_key_shows_only_that_it_is_set(logged_in_page: Page, server_url, server_keys):
    page = logged_in_page
    page.goto(f"{server_url}{reverse('ai-keys')}")
    openai = key_row(page, "OPENAI_API_KEY")

    openai.locator(".key-input").fill("sk-12345")
    openai.locator(".key-save").click()

    expect(openai.locator(".key-source")).to_have_text("Your key")


@pytest.mark.parametrize(
    ("cookie", "message"),
    [
        (
            settings.SESSION_COOKIE_NAME,
            "Your session has ended. Reload the page, sign in and try again.",
        ),
        (
            settings.CSRF_COOKIE_NAME,
            "The server refused the request (403). Reload the page and try again.",
        ),
    ],
)
def test_a_reply_that_is_not_json_shows_a_readable_message(
    logged_in_page: Page, server_url, approved_user, server_keys, cookie, message
):
    page = logged_in_page
    page.goto(f"{server_url}{reverse('ai-keys')}")
    page.context.clear_cookies(name=cookie)
    openai = key_row(page, "OPENAI_API_KEY")

    openai.locator(".key-input").fill(OWN_KEY)
    openai.locator(".key-save").click()

    expect(page.get_by_role("alert")).to_have_text(f"OpenAI: {message}")
    assert key_store.own_key(approved_user.id, "OPENAI_API_KEY") is None


def test_the_no_key_alert_links_to_the_keys_page(reader: ReaderPage, fake_stream, server_keys):
    fake_stream.scripts["page"] = [
        lambda req: ArticleEvent.error(
            article_error(NoLLMAvailableError("none", reason="no_keys"), req, had_text=False),
        ),
    ]
    reader.open_sidebar()
    reader.click_word("page")
    panel = reader.panel(1)
    expect(panel).to_contain_text("You have no free pool key of your own")

    panel.get_by_role("link", name="AI keys page").click()

    expect(reader.page).to_have_url(f"{reader.server_url}{reverse('ai-keys')}")
    expect(key_row(reader.page, "GROQ_API_KEY")).to_be_visible()
