import importlib

import allure
import pytest
from django.contrib.auth import get_user_model

from lexiflux.language import key_store
from lexiflux.models import AIKey

KEY = "sk-test-own-1234567890abcd"


@pytest.fixture
def owner(db):
    return get_user_model().objects.create_user(
        username="owner", email="owner@example.com", password="x"
    )


@allure.epic("AI keys")
@allure.feature("Key store")
def test_a_saved_key_is_stored_encrypted_and_read_back(owner):
    key_store.save_own_key(owner, "OPENAI_API_KEY", KEY)

    (row,) = AIKey.objects.all()
    assert (row.user_id, row.ref) == (owner.id, "OPENAI_API_KEY")
    assert KEY not in row.encrypted
    assert key_store.own_key(owner.id, "OPENAI_API_KEY") == KEY
    assert key_store.own_keys(owner.id) == {"OPENAI_API_KEY": KEY}


@allure.epic("AI keys")
@allure.feature("Key store")
def test_saving_again_replaces_the_key(owner):
    key_store.save_own_key(owner, "OPENAI_API_KEY", KEY)
    key_store.save_own_key(owner, "OPENAI_API_KEY", "sk-replacement")

    assert AIKey.objects.count() == 1
    assert key_store.own_key(owner.id, "OPENAI_API_KEY") == "sk-replacement"


@allure.epic("AI keys")
@allure.feature("Key store")
def test_clearing_removes_only_that_key(owner):
    key_store.save_own_key(owner, "OPENAI_API_KEY", KEY)
    key_store.save_own_key(owner, "GROQ_API_KEY", "gsk-own")

    key_store.clear_own_key(owner, "OPENAI_API_KEY")

    assert key_store.own_keys(owner.id) == {"GROQ_API_KEY": "gsk-own"}


@allure.epic("AI keys")
@allure.feature("Key store")
def test_a_key_saved_under_another_secret_key_counts_as_not_set(owner, settings):
    key_store.save_own_key(owner, "OPENAI_API_KEY", KEY)
    key_store.save_own_key(owner, "GROQ_API_KEY", "gsk-own")
    AIKey.objects.filter(ref="GROQ_API_KEY").update(encrypted="not-a-fernet-token")

    assert key_store.own_key(owner.id, "GROQ_API_KEY") is None
    settings.SECRET_KEY = "rotated"
    assert key_store.own_key(owner.id, "OPENAI_API_KEY") is None
    assert key_store.own_keys(owner.id) == {}


@allure.epic("AI keys")
@allure.feature("Key store")
def test_scoped_refs_name_every_saved_key_under_its_user_scope(owner):
    other = get_user_model().objects.create_user(
        username="other", email="other@example.com", password="x"
    )
    key_store.save_own_key(owner, "OPENAI_API_KEY", KEY)
    key_store.save_own_key(other, "GROQ_API_KEY", "gsk-other")

    assert key_store.scoped_refs() == {
        f"u-{owner.id}/OPENAI_API_KEY",
        f"u-{other.id}/GROQ_API_KEY",
    }


@allure.epic("AI keys")
@allure.feature("Key store")
@pytest.mark.parametrize(
    ("scope", "user_id"),
    [("u-5", 5), ("u-123", 123), ("u-", None), ("x-5", None), ("u-5/x", None), ("", None)],
)
def test_user_of_scope(scope, user_id):
    assert key_store.user_of(scope) == user_id
    if user_id is not None:
        assert key_store.scope_of(user_id) == scope


@allure.epic("AI keys")
@allure.feature("Key store")
def test_docker_secret_key_is_the_operators_else_the_one_generated_next_to_the_database(
    tmp_path, monkeypatch
):
    docker = importlib.import_module("lexiflux.environments.docker")
    monkeypatch.setattr(docker, "BASE_DIR", tmp_path)
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    assert docker._secret_key() == ""

    (tmp_path / ".secret_key").write_text("generated-on-first-start\n")
    assert docker._secret_key() == "generated-on-first-start"

    monkeypatch.setenv("DJANGO_SECRET_KEY", "set-by-the-operator")
    assert docker._secret_key() == "set-by-the-operator"
