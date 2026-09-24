import importlib
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import allure
import llmbroker
import llmbroker.home
import pytest
from django.conf import settings

from lexiflux.language import broker


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
        patch("lexiflux.language.broker.llmbroker.Broker") as broker_cls,
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
    assert isinstance(kwargs["secrets"], llmbroker.Secrets)
    assert kwargs["secrets"]._env_file == Path(settings.BASE_DIR) / ".env"
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
