import asyncio
import importlib
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import allure
import llmbroker
import llmbroker.home
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from llmbroker.protocols.secrets import EnumerableSecretsProtocol, MutableSecretsProtocol

from lexiflux.language import broker, key_store


# Taken at import, before the suite-wide guard replaces it for each test.
REAL_GET_BROKER = broker.get_broker


@pytest.fixture(autouse=True)
def real_get_broker():
    with patch("lexiflux.language.broker.get_broker", REAL_GET_BROKER):
        yield


@pytest.fixture
def fresh_broker():
    broker._broker = None
    with (
        patch("lexiflux.language.broker.RebuildableBroker") as broker_cls,
        patch("lexiflux.language.broker.atexit.register") as register,
    ):
        yield SimpleNamespace(cls=broker_cls, register=register)
    broker._broker = None


@allure.epic("AI articles")
@allure.feature("Broker")
def test_one_broker_per_process(fresh_broker):
    first = broker.get_broker()
    second = broker.get_broker()
    assert first is second
    assert fresh_broker.cls.call_count == 1
    fresh_broker.register.assert_called_once_with(first.close)


@allure.epic("AI articles")
@allure.feature("Broker")
def test_local_uses_its_home_and_env_file_secrets(fresh_broker):
    broker.get_broker()
    args, kwargs = fresh_broker.cls.call_args
    assert args == (None,)
    assert settings.LLMBROKER_DATASOURCE is None
    assert kwargs["home"] == settings.LLMBROKER_HOME
    assert isinstance(kwargs["secrets"], broker.KeySecrets)
    assert kwargs["secrets"]._server._env_file == Path(settings.BASE_DIR) / ".env"
    assert kwargs["direct"] == ["gpt", "gpt-fast", "opus"]


@allure.epic("AI articles")
@allure.feature("Broker")
def test_datasource_follows_settings(fresh_broker, settings):
    settings.LLMBROKER_DATASOURCE = "postgresql://u:p@db:5432/lexiflux"
    broker.get_broker()
    assert fresh_broker.cls.call_args.args == ("postgresql://u:p@db:5432/lexiflux",)


@allure.epic("AI articles")
@allure.feature("Broker")
@pytest.mark.parametrize("module", ["lexiflux.environments.local", "lexiflux.environments.docker"])
def test_local_and_docker_environments_use_lexiflux_llmbroker_home(module):
    environment = importlib.import_module(module)
    assert environment.LLMBROKER_DATASOURCE is None
    assert environment.LLMBROKER_HOME == environment.BASE_DIR / ".llmbroker"


@allure.epic("AI articles")
@allure.feature("Broker")
@pytest.mark.parametrize(
    "database_url",
    ["postgres://u:p@db:5432/lexiflux", "postgresql://u:p@db:5432/lexiflux"],
)
def test_koyeb_environment_uses_database_url(database_url):
    env = {"DATABASE_URL": database_url, "SECRET_KEY": "test"}
    fake_dj_database_url = SimpleNamespace(parse=lambda url, **kwargs: {"NAME": url})
    with (
        patch.dict(os.environ, env),
        patch.dict(sys.modules, {"dj_database_url": fake_dj_database_url}),
    ):
        sys.modules.pop("lexiflux.environments.koyeb", None)
        koyeb = importlib.import_module("lexiflux.environments.koyeb")
    assert koyeb.LLMBROKER_DATASOURCE == "postgresql://u:p@db:5432/lexiflux"
    assert koyeb.LLMBROKER_HOME is None


@allure.epic("AI articles")
@allure.feature("Broker")
def test_llms_for_scopes_by_user(fresh_broker):
    llms = broker.llms_for(SimpleNamespace(id=42))
    fresh_broker.cls.return_value.for_scope.assert_called_once_with("u-42")
    assert llms is fresh_broker.cls.return_value.for_scope.return_value


def pool_snapshot(**disabled: bool) -> dict[str, SimpleNamespace]:
    return {name: SimpleNamespace(disabled=flag) for name, flag in disabled.items()}


@allure.epic("AI articles")
@allure.feature("Broker")
def test_get_broker_disables_the_excluded_pool_models(fresh_broker):
    instance = fresh_broker.cls.return_value
    instance.snapshot.return_value = pool_snapshot(
        **{"groq-gpt-oss-120b": False, **dict.fromkeys(broker.EXCLUDED_POOL_LLMS, False)},
    )
    broker.get_broker()
    broker.get_broker()
    assert set(broker.EXCLUDED_POOL_LLMS) == {
        "openrouter-nemotron-3-ultra",
        "openrouter-laguna-s-2.1",
    }
    assert [c.args[0] for c in instance.disable_llm.call_args_list] == list(
        broker.EXCLUDED_POOL_LLMS,
    )


@allure.epic("AI articles")
@allure.feature("Broker")
def test_get_broker_skips_models_already_disabled_in_the_store(fresh_broker):
    instance = fresh_broker.cls.return_value
    instance.snapshot.return_value = pool_snapshot(**dict.fromkeys(broker.EXCLUDED_POOL_LLMS, True))
    broker.get_broker()
    instance.disable_llm.assert_not_called()


@allure.epic("AI articles")
@allure.feature("Broker")
def test_an_excluded_name_missing_from_the_catalog_is_logged_not_fatal(fresh_broker, caplog):
    instance = fresh_broker.cls.return_value
    instance.snapshot.return_value = pool_snapshot(**{"openrouter-laguna-s-2.1": False})
    with patch.object(broker, "EXCLUDED_POOL_LLMS", ("gone-llm", "openrouter-laguna-s-2.1")):
        assert broker.get_broker() is instance
    instance.disable_llm.assert_called_once_with("openrouter-laguna-s-2.1")
    assert "gone-llm" in caplog.text


@allure.epic("AI articles")
@allure.feature("Broker")
def test_a_failed_exclusion_is_retried_on_the_next_call(fresh_broker):
    instance = fresh_broker.cls.return_value
    instance.snapshot.side_effect = [RuntimeError("catalog empty"), {}]
    with pytest.raises(RuntimeError):
        broker.get_broker()
    assert broker.get_broker() is instance
    assert fresh_broker.cls.call_count == 1
    assert instance.snapshot.call_count == 2


@allure.epic("AI articles")
@allure.feature("Broker")
def test_pool_keys_omit_keys_that_serve_only_excluded_models():
    configs = [
        SimpleNamespace(name="openrouter-nemotron-3-ultra", api_key_ref="OPENROUTER_API_KEY"),
        SimpleNamespace(name="openrouter-laguna-s-2.1", api_key_ref="OPENROUTER_API_KEY"),
        SimpleNamespace(name="groq-gpt-oss-120b", api_key_ref="GROQ_API_KEY"),
        SimpleNamespace(name="openrouter-other", api_key_ref="SHARED_API_KEY"),
        SimpleNamespace(name="openrouter-laguna-s-2.1", api_key_ref="SHARED_API_KEY"),
    ]
    keys = dict.fromkeys(("OPENROUTER_API_KEY", "GROQ_API_KEY", "SHARED_API_KEY"), "help")
    pool = SimpleNamespace(configs=configs, keys=keys)
    with patch("lexiflux.language.broker.llmbroker.curated_pool", return_value=pool) as curated:
        assert list(broker.pool_keys()) == ["GROQ_API_KEY", "SHARED_API_KEY"]
    curated.assert_called_once_with(home=settings.LLMBROKER_HOME)


@allure.epic("AI articles")
@allure.feature("Broker")
def test_tests_never_use_a_real_llmbroker_home():
    home = Path(settings.LLMBROKER_HOME).resolve()
    assert home != (Path(settings.BASE_DIR) / ".llmbroker").resolve()
    assert Path(tempfile.gettempdir()).resolve() in home.parents
    resolved = llmbroker.home.home_dir_for_read().resolve()
    assert resolved == home
    assert resolved != (Path.home() / "Library" / "Caches" / "llmbroker").resolve()


@pytest.fixture
def server_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GROQ_API_KEY=gsk-from-env-file\nZAI_API_KEY=\n# OPENAI_API_KEY=commented\n")
    monkeypatch.setattr(broker, "env_file", lambda: env)
    for name in ("GROQ_API_KEY", "ZAI_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-from-environment")
    return env


@pytest.fixture
def key_owner(db):
    return get_user_model().objects.create_user(
        username="key-owner", email="key-owner@example.com", password="x"
    )


def run_async(coro):
    # Playwright tests earlier in the session leave an event loop running in this thread.
    with ThreadPoolExecutor(1) as pool:
        return pool.submit(asyncio.run, coro).result()


def resolve(secrets: broker.KeySecrets, ref: str) -> str | None:
    try:
        return run_async(secrets.resolve(ref))
    except KeyError:
        return None


@allure.epic("AI keys")
@allure.feature("Broker secrets")
def test_server_refs_are_the_environment_then_env_file_without_blank_values(server_env):
    refs = broker.server_refs()
    assert {"GROQ_API_KEY", "GEMINI_API_KEY"} <= refs
    assert "ZAI_API_KEY" not in refs
    assert "OPENAI_API_KEY" not in refs


@allure.epic("AI keys")
@allure.feature("Broker secrets")
@pytest.mark.django_db(transaction=True)
def test_shared_refs_resolve_from_the_server_and_scoped_refs_from_the_database(
    server_env, key_owner
):
    key_store.save_own_key(key_owner, "GROQ_API_KEY", "gsk-own")
    secrets = broker.KeySecrets(server_env)

    assert resolve(secrets, "GROQ_API_KEY") == "gsk-from-env-file"
    assert resolve(secrets, "GEMINI_API_KEY") == "gemini-from-environment"
    assert resolve(secrets, f"u-{key_owner.id}/GROQ_API_KEY") == "gsk-own"
    # The broker falls back to the shared ref itself; the backend never does.
    assert resolve(secrets, f"u-{key_owner.id}/GEMINI_API_KEY") is None
    assert resolve(secrets, "u-99999/GROQ_API_KEY") is None
    assert resolve(secrets, "team-1/GROQ_API_KEY") is None


@allure.epic("AI keys")
@allure.feature("Broker secrets")
@pytest.mark.django_db(transaction=True)
def test_the_listing_names_the_server_keys_and_every_saved_key(server_env, key_owner):
    key_store.save_own_key(key_owner, "OPENAI_API_KEY", "sk-own")
    secrets = broker.KeySecrets(server_env)

    refs = run_async(secrets.refs())
    assert {"GROQ_API_KEY", "GEMINI_API_KEY", f"u-{key_owner.id}/OPENAI_API_KEY"} <= refs
    assert run_async(secrets.refs(f"u-{key_owner.id}/")) == {f"u-{key_owner.id}/OPENAI_API_KEY"}


@allure.epic("AI keys")
@allure.feature("Broker secrets")
def test_the_backend_is_enumerable_and_read_only():
    secrets = broker.KeySecrets(Path("/nonexistent/.env"))
    assert isinstance(secrets, EnumerableSecretsProtocol)
    # A settable backend would get the server's keys copied into it by llmbroker.
    assert not isinstance(secrets, MutableSecretsProtocol)


@allure.epic("AI keys")
@allure.feature("Broker secrets")
def test_refresh_keys_without_a_broker_does_nothing():
    broker._broker = None
    broker.refresh_keys()
    assert broker._broker is None


@allure.epic("AI keys")
@allure.feature("Broker secrets")
def test_refresh_keys_rebuilds_the_running_broker(fresh_broker):
    running = broker.get_broker()
    broker.refresh_keys()
    running.rebuild.assert_called_once_with()


@allure.epic("AI keys")
@allure.feature("Broker secrets")
def test_a_failed_refresh_is_logged_not_raised(fresh_broker, caplog):
    running = broker.get_broker()
    running.rebuild.side_effect = RuntimeError("registry unreachable")
    broker.refresh_keys()
    assert "Could not re-read the AI keys" in caplog.text
