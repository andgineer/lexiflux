import json
from unittest.mock import patch

import allure
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from lexiflux.language import key_store
from lexiflux.models import AIKey

OWN_KEY = "sk-alice-own-secret-7x9q"
SERVER_KEY = "sk-server-secret-value-3k2m"


@pytest.fixture
def alice(db):
    return get_user_model().objects.create_user(
        username="alice", email="alice@example.com", password="x", is_approved=True
    )


@pytest.fixture
def bob(db):
    return get_user_model().objects.create_user(
        username="bob", email="bob@example.com", password="x", is_approved=True
    )


@pytest.fixture
def refresh():
    with patch("lexiflux.views.ai_keys_views.refresh_keys") as refresh:
        yield refresh


def page_keys(client) -> dict[str, dict]:
    response = client.get(reverse("ai-keys"))
    assert response.status_code == 200
    return {row["ref"]: row for row in response.context["keys"]}


def save(client, ref: str, value: object):
    return client.post(
        reverse("ai_key_api", args=[ref]),
        data=json.dumps({"key": value}),
        content_type="application/json",
    )


def clear(client, ref: str):
    return client.delete(reverse("ai_key_api", args=[ref]))


@allure.epic("AI keys")
@allure.feature("AI keys page")
def test_the_page_lists_every_key_with_its_hint_and_whose_it_is(client, alice, server_keys):
    server_keys("GROQ_API_KEY", SERVER_KEY)
    client.force_login(alice)

    response = client.get(reverse("ai-keys"))
    content = response.content.decode()
    keys = {row["ref"]: row for row in response.context["keys"]}

    assert list(keys) == [
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "ZAI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]
    assert keys["GROQ_API_KEY"]["source"] == "server"
    assert keys["OPENAI_API_KEY"]["source"] == "none"
    assert 'href=\\"https://console.groq.com/keys\\" target=\\"_blank\\"' in content
    assert keys["GROQ_API_KEY"]["effort"] == "Free signup"
    # llmbroker's own rating of the provider ("value = good") is not for users.
    assert "good" not in json.dumps(keys["GROQ_API_KEY"])
    assert SERVER_KEY not in content
    assert "AI Keys" in content


@allure.epic("AI keys")
@allure.feature("AI keys page")
def test_the_menu_links_to_the_page(client, approved_user):
    client.force_login(approved_user)
    content = client.get(reverse("library")).content.decode()
    assert f'href="{reverse("ai-keys")}">AI Keys</a>' in content


@allure.epic("AI keys")
@allure.feature("AI keys page")
@pytest.mark.usefixtures("server_keys")
def test_save_replace_and_clear(client, alice, refresh):
    client.force_login(alice)

    saved = save(client, "OPENAI_API_KEY", f"  {OWN_KEY}\n")
    assert saved.status_code == 200
    assert saved.json()["key"]["source"] == "own"
    assert saved.json()["key"]["last4"] == OWN_KEY[-4:]
    assert key_store.own_key(alice.id, "OPENAI_API_KEY") == OWN_KEY

    replaced = save(client, "OPENAI_API_KEY", "sk-replacement-abcd")
    assert replaced.json()["key"]["last4"] == "abcd"
    assert key_store.own_key(alice.id, "OPENAI_API_KEY") == "sk-replacement-abcd"
    assert AIKey.objects.filter(user=alice).count() == 1

    cleared = clear(client, "OPENAI_API_KEY")
    assert cleared.status_code == 200
    assert cleared.json()["key"]["source"] == "none"
    assert not AIKey.objects.filter(user=alice).exists()
    assert refresh.call_count == 3


@allure.epic("AI keys")
@allure.feature("AI keys page")
@pytest.mark.usefixtures("server_keys")
def test_the_saved_value_never_goes_back_to_the_browser(client, alice, refresh):
    client.force_login(alice)

    saved = save(client, "OPENAI_API_KEY", OWN_KEY)
    content = client.get(reverse("ai-keys")).content.decode()

    assert OWN_KEY not in saved.content.decode()
    assert OWN_KEY not in content
    assert OWN_KEY[-4:] in content


@allure.epic("AI keys")
@allure.feature("AI keys page")
@pytest.mark.parametrize("value", ["", "   \n", None, 42])
def test_a_blank_key_is_not_saved(client, alice, refresh, value):
    client.force_login(alice)

    response = save(client, "OPENAI_API_KEY", value)

    assert response.status_code == 400
    assert "Enter a key" in response.json()["error"]
    assert not AIKey.objects.exists()
    refresh.assert_not_called()


@allure.epic("AI keys")
@allure.feature("AI keys page")
def test_a_blank_save_keeps_the_saved_key(client, alice, refresh):
    key_store.save_own_key(alice, "OPENAI_API_KEY", OWN_KEY)
    client.force_login(alice)

    assert save(client, "OPENAI_API_KEY", " ").status_code == 400
    assert key_store.own_key(alice.id, "OPENAI_API_KEY") == OWN_KEY


@allure.epic("AI keys")
@allure.feature("AI keys page")
@pytest.mark.parametrize("ref", ["OPENROUTER_API_KEY", "PATH", "u-1"])
def test_only_the_listed_keys_can_be_saved(client, alice, refresh, ref):
    client.force_login(alice)

    assert save(client, ref, OWN_KEY).status_code == 404
    assert clear(client, ref).status_code == 404
    assert not AIKey.objects.exists()


@allure.epic("AI keys")
@allure.feature("AI keys page")
def test_the_api_takes_no_get(client, alice):
    client.force_login(alice)
    assert client.get(reverse("ai_key_api", args=["OPENAI_API_KEY"])).status_code == 405


@allure.epic("AI keys")
@allure.feature("AI keys page")
@pytest.mark.usefixtures("server_keys")
def test_another_users_keys_are_invisible_and_untouched(client, alice, bob, refresh):
    key_store.save_own_key(alice, "OPENAI_API_KEY", OWN_KEY)
    client.force_login(bob)

    keys = page_keys(client)
    content = client.get(reverse("ai-keys")).content.decode()
    clear(client, "OPENAI_API_KEY")

    assert keys["OPENAI_API_KEY"]["source"] == "none"
    assert keys["OPENAI_API_KEY"]["last4"] == ""
    assert OWN_KEY[-4:] not in content
    assert key_store.own_key(alice.id, "OPENAI_API_KEY") == OWN_KEY


@allure.epic("AI keys")
@allure.feature("AI keys page")
@pytest.mark.usefixtures("server_keys")
def test_an_undecryptable_key_shows_as_not_set(client, alice, settings, refresh):
    key_store.save_own_key(alice, "OPENAI_API_KEY", OWN_KEY)
    settings.SECRET_KEY = "rotated-secret-key"
    client.force_login(alice)

    assert page_keys(client)["OPENAI_API_KEY"]["source"] == "none"
    assert save(client, "OPENAI_API_KEY", "sk-new-after-rotation").status_code == 200
    assert key_store.own_key(alice.id, "OPENAI_API_KEY") == "sk-new-after-rotation"


@allure.epic("AI keys")
@allure.feature("AI keys page")
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", reverse("ai-keys")),
        ("post", reverse("ai_key_api", args=["OPENAI_API_KEY"])),
        ("delete", reverse("ai_key_api", args=["OPENAI_API_KEY"])),
    ],
)
def test_multi_user_mode_requires_login(client, method, url):
    response = getattr(client, method)(url)
    assert response.status_code == 302
    assert reverse("login") in response["Location"]
    assert not AIKey.objects.exists()
