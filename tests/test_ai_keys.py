from unittest.mock import patch

import allure
import llmbroker
import pytest
from django.contrib.auth import get_user_model

from lexiflux.language import ai_keys, key_store
from lexiflux.language.ai_keys import NONE, OWN, SERVER, hint_html, key_rows

SERVED_POOL_REFS = ["GROQ_API_KEY", "GEMINI_API_KEY", "ZAI_API_KEY"]


@allure.epic("AI keys")
@allure.feature("Keys from llmbroker")
def test_the_keys_are_the_served_pool_keys_then_the_paid_providers():
    keys = ai_keys.ai_keys()

    assert [key.ref for key in keys] == [*SERVED_POOL_REFS, "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    assert [key.pool for key in keys] == [True, True, True, False, False]
    assert "OPENROUTER_API_KEY" not in [key.ref for key in keys]


@allure.epic("AI keys")
@allure.feature("Keys from llmbroker")
def test_every_hint_is_llmbrokers_own_key_help():
    pool = llmbroker.curated_pool().keys
    providers = {p.api_key_ref: p for p in llmbroker.curated_providers()}

    for key in ai_keys.ai_keys():
        expected = pool[key.ref].help if key.pool else providers[key.ref].key_help
        assert key.hint == expected
        assert key.hint.strip()


@allure.epic("AI keys")
@allure.feature("Keys from llmbroker")
def test_the_signup_effort_is_shown_in_plain_words():
    efforts = {key.ref: key.effort for key in ai_keys.ai_keys()}

    assert efforts["GROQ_API_KEY"] == "Free signup"
    assert efforts["GEMINI_API_KEY"] == "Sign in with your account"
    assert efforts["OPENAI_API_KEY"] == ""


@allure.epic("AI keys")
@allure.feature("Keys from llmbroker")
@pytest.mark.parametrize(
    ("extra", "effort"),
    [
        ({"effort": "signup", "value": "high"}, "Free signup"),
        ({"effort": "carrier-pigeon"}, ""),
        ({"value": "high"}, ""),
    ],
)
def test_an_unknown_or_missing_effort_is_not_shown(extra, effort):
    info = llmbroker.KeyInfo(api_key_ref="GROQ_API_KEY", help="Get a key.", extra=extra)
    with patch("lexiflux.language.ai_keys.pool_keys", return_value={"GROQ_API_KEY": info}):
        groq = next(key for key in ai_keys.ai_keys() if key.ref == "GROQ_API_KEY")
    assert groq.effort == effort


@allure.epic("AI keys")
@allure.feature("Keys from llmbroker")
def test_names_come_from_the_provider_label_or_the_hints_link():
    names = {key.ref: key.name for key in ai_keys.ai_keys()}

    assert names["OPENAI_API_KEY"] == "OpenAI"
    assert names["ANTHROPIC_API_KEY"] == "Anthropic (Claude)"
    assert names["GEMINI_API_KEY"] == "Google (Gemini)"
    assert names["GROQ_API_KEY"] == "Groq"
    assert names["ZAI_API_KEY"] == "Z.ai"


@allure.epic("AI keys")
@allure.feature("Keys from llmbroker")
def test_a_provider_whose_models_all_left_the_catalog_is_not_listed():
    with patch("lexiflux.language.ai_keys.is_available", side_effect=lambda model: model != "opus"):
        refs = [key.ref for key in ai_keys.ai_keys()]
    assert "ANTHROPIC_API_KEY" not in refs
    assert "OPENAI_API_KEY" in refs


@allure.epic("AI keys")
@allure.feature("Keys from llmbroker")
@pytest.mark.parametrize(
    ("text", "html"),
    [
        (
            "Create a free API key at [groq](https://console.groq.com/keys) (sign in).",
            'Create a free API key at <a href="https://console.groq.com/keys" target="_blank"'
            ' rel="noopener">groq</a> (sign in).',
        ),
        (
            "Create a key at https://platform.openai.com/api-keys (paid).",
            'Create a key at <a href="https://platform.openai.com/api-keys" target="_blank"'
            ' rel="noopener">https://platform.openai.com/api-keys</a> (paid).',
        ),
        (
            "See https://console.anthropic.com/.",
            'See <a href="https://console.anthropic.com/" target="_blank" rel="noopener">'
            "https://console.anthropic.com/</a>.",
        ),
        ("<b>no link</b>", "&lt;b&gt;no link&lt;/b&gt;"),
    ],
)
def test_hint_html(text, html):
    assert hint_html(text) == html


@allure.epic("AI keys")
@allure.feature("Keys from llmbroker")
def test_hint_html_escapes_quotes_in_links():
    text = hint_html('[key](https://x.io/a"onmouseover="alert(1)) and "q"', "alert-link")
    assert '"onmouseover="' not in text
    assert "&quot;" in text
    assert text.startswith('<a href="https://x.io/a&quot;onmouseover=&quot;alert(1"')
    assert 'class="alert-link"' in text


@allure.epic("AI keys")
@allure.feature("Key status")
@pytest.mark.django_db
def test_rows_say_whose_key_it_is_and_carry_only_the_last_4_characters(server_keys):
    user = get_user_model().objects.create_user(username="u", email="u@example.com", password="x")
    server_keys("GROQ_API_KEY", "gsk-server-secret-value")
    key_store.save_own_key(user, "OPENAI_API_KEY", "sk-own-secret-value-wxyz")
    key_store.save_own_key(user, "GROQ_API_KEY", "gsk-own-secret-value-abcd")

    rows = {row["ref"]: row for row in key_rows(user.id)}

    assert (rows["OPENAI_API_KEY"]["source"], rows["OPENAI_API_KEY"]["last4"]) == (OWN, "wxyz")
    assert (rows["GROQ_API_KEY"]["source"], rows["GROQ_API_KEY"]["last4"]) == (OWN, "abcd")
    assert (rows["ZAI_API_KEY"]["source"], rows["ZAI_API_KEY"]["last4"]) == (NONE, "")
    assert "secret-value" not in str(rows)

    key_store.clear_own_key(user, "GROQ_API_KEY")
    (groq,) = key_rows(user.id, {"GROQ_API_KEY"})
    assert (groq["source"], groq["last4"]) == (SERVER, "")


@allure.epic("AI keys")
@allure.feature("Key status")
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("value", "last4"),
    [("abcd", ""), ("sk-12345", ""), ("sk-123456", "3456"), ("sk-own-secret-wxyz", "wxyz")],
)
def test_a_key_of_8_characters_or_fewer_shows_only_that_it_is_set(value, last4):
    user = get_user_model().objects.create_user(username="u", email="u@example.com", password="x")
    key_store.save_own_key(user, "OPENAI_API_KEY", value)

    (row,) = key_rows(user.id, {"OPENAI_API_KEY"})

    assert (row["source"], row["last4"]) == (OWN, last4)
