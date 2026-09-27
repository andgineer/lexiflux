import pytest
from django.urls import reverse
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.django_db(transaction=True)


def test_changing_the_model_resets_the_knobs(
    logged_in_page: Page, server_url, language_preferences
):
    page = logged_in_page
    page.goto(f"{server_url}{reverse('language-preferences')}")
    card = page.locator(".list-group-item", has=page.locator("h5", has_text="In depth"))
    card.get_by_role("button", name="Edit").click()

    modal = page.locator("#articleModal")
    expect(modal).to_be_visible()
    model, effort, tier = (
        modal.locator("#model-select"),
        modal.locator("#effort-select"),
        modal.locator("#tier-select"),
    )
    note = modal.locator("#priority-note")
    expect(model).to_have_value("gpt")
    expect(effort).to_have_value("none")
    expect(tier).to_have_value("priority")
    expect(note).to_be_visible()

    tier.select_option("standard")
    expect(note).to_be_hidden()

    model.select_option("opus")
    expect(effort).to_have_value("low")
    expect(tier).to_have_count(0)

    model.select_option("gpt-fast")
    expect(effort).to_have_value("low")
    expect(tier).to_have_value("priority")
    expect(note).to_be_visible()

    effort.select_option("high")
    model.select_option("pool")
    expect(effort).to_have_count(0)
    expect(tier).to_have_count(0)

    model.select_option("gpt")
    expect(effort).to_have_value("none")
    expect(tier).to_have_value("priority")


def test_dictionary_hint_follows_the_selected_translator(
    logged_in_page: Page, server_url, language_preferences
):
    page = logged_in_page
    page.goto(f"{server_url}{reverse('language-preferences')}")
    page.locator("#inline-translation-edit").click()

    modal = page.locator("#articleModal")
    expect(modal).to_be_visible()
    dictionary, hint = modal.locator("#dictionary-select"), modal.locator("#dictionary-hint")
    expect(dictionary).to_have_value("LLMTranslation")
    expect(hint).to_contain_text("Best for the inline popup")

    dictionary.select_option("Wiktionary")
    expect(hint).to_contain_text("Best as a sidebar article")

    dictionary.select_option("Google")
    expect(hint).to_contain_text("without its sentence")
