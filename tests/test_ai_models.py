from unittest.mock import patch

import allure
import pytest
from django.core.exceptions import ValidationError

from lexiflux.language.ai_models import (
    OFFERED_MODELS,
    default_knobs,
    editor_models,
    is_available,
    provider_of,
    request_params,
    validate_knobs,
)
from lexiflux.models import LexicalArticle


@allure.epic("AI articles")
@allure.feature("Knobs")
@pytest.mark.parametrize(
    "model, effort, tier, expected",
    [
        ("gpt", None, None, {}),
        ("gpt", "none", None, {"reasoning_effort": "none"}),
        ("gpt", "low", None, {"reasoning_effort": "low"}),
        ("gpt", "medium", None, {"reasoning_effort": "medium"}),
        ("gpt", "high", None, {"reasoning_effort": "high"}),
        ("gpt", None, "priority", {"service_tier": "priority"}),
        ("gpt", None, "standard", {}),
        ("gpt", "none", "priority", {"reasoning_effort": "none", "service_tier": "priority"}),
        ("gpt-fast", "low", "priority", {"reasoning_effort": "low", "service_tier": "priority"}),
        ("gpt-fast", "high", "standard", {"reasoning_effort": "high"}),
        ("opus", None, None, {}),
        ("opus", "none", None, {"thinking": {"type": "disabled"}}),
        ("opus", "low", None, {"reasoning_effort": "low"}),
        ("opus", "medium", None, {"reasoning_effort": "medium"}),
        ("opus", "high", None, {"reasoning_effort": "high"}),
        ("pool", None, None, {}),
    ],
)
def test_request_params(model, effort, tier, expected):
    assert request_params(model, effort, tier) == expected


@allure.epic("AI articles")
@allure.feature("Knobs")
@pytest.mark.parametrize(
    "model, effort, tier",
    [
        ("opus", None, "priority"),
        ("opus", None, "standard"),
        ("pool", "low", None),
        ("pool", None, "priority"),
        ("gpt", "extreme", None),
        ("gpt", None, "flex"),
        ("claude-sonnet-4-5", None, None),
    ],
)
def test_invalid_knobs_rejected(model, effort, tier):
    with pytest.raises(ValueError):
        validate_knobs(model, effort, tier)
    with pytest.raises(ValueError):
        request_params(model, effort, tier)


@allure.epic("AI articles")
@allure.feature("Knobs")
@pytest.mark.parametrize(
    "model, expected",
    [
        ("pool", {}),
        ("gpt", {"effort": "none", "tier": "priority"}),
        ("gpt-fast", {"effort": "low", "tier": "priority"}),
        ("opus", {"effort": "low"}),
    ],
)
def test_default_knobs(model, expected):
    assert default_knobs(model) == expected


@allure.epic("AI articles")
@allure.feature("Offered models")
def test_offered_models():
    assert set(OFFERED_MODELS) == {"pool", "gpt", "gpt-fast", "opus"}


@allure.epic("AI articles")
@allure.feature("Offered models")
def test_provider_of_reads_catalog():
    assert provider_of("gpt") == "openai"
    assert provider_of("gpt-fast") == "openai"
    assert provider_of("opus") == "anthropic"
    assert provider_of("no-such-alias") is None


@allure.epic("AI articles")
@allure.feature("Offered models")
def test_dropped_alias_makes_option_unavailable():
    assert is_available("gpt")
    with patch(
        "lexiflux.language.ai_models._catalog_providers", return_value={"opus": "anthropic"}
    ):
        assert not is_available("gpt")
        assert is_available("opus")
        assert is_available("pool")
        assert [model["key"] for model in editor_models()] == ["pool", "opus"]


@allure.epic("AI articles")
@allure.feature("Offered models")
def test_editor_models():
    models = {model["key"]: model for model in editor_models()}
    assert models["gpt"]["efforts"] == ["none", "low", "medium", "high"]
    assert models["gpt"]["tiers"] == ["priority", "standard"]
    assert models["gpt"]["defaults"] == {"effort": "none", "tier": "priority"}
    assert models["opus"]["tiers"] == []
    assert models["pool"]["efforts"] == []
    assert models["pool"]["provider"] is None


@allure.epic("AI articles")
@allure.feature("Knobs")
@pytest.mark.django_db
class TestLexicalArticleClean:
    def make(self, article_type, parameters):
        return LexicalArticle(type=article_type, title="t", parameters=parameters)

    @pytest.mark.parametrize(
        "article_type, parameters",
        [
            ("AI dictionary", {"model": "pool"}),
            ("In depth", {"model": "gpt", "effort": "none", "tier": "priority"}),
            ("Sentence", {"model": "gpt-fast"}),
            ("Origin", {"model": "opus", "effort": "low"}),
            ("AI", {"model": "gpt", "prompt": "Synonyms, please."}),
        ],
    )
    def test_valid(self, article_type, parameters):
        self.make(article_type, parameters).clean()

    @pytest.mark.parametrize(
        "article_type, parameters",
        [
            ("AI dictionary", {"model": "pool", "effort": "low"}),
            ("In depth", {"model": "gpt", "effort": "extreme"}),
            ("Explain", {"model": "opus", "tier": "priority"}),
            ("Translate", {"model": "gpt-5.1"}),
            ("Lexical", {}),
            ("AI", {"model": "gpt"}),
            ("AI", {"prompt": "no model"}),
        ],
    )
    def test_invalid(self, article_type, parameters):
        with pytest.raises(ValidationError):
            self.make(article_type, parameters).clean()
