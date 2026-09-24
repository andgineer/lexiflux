from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from django.conf import settings
from llmbroker import curated_paid

POOL = "pool"

OPENAI = "openai"
ANTHROPIC = "anthropic"

EFFORT_NONE = "none"
TIER_PRIORITY = "priority"
TIER_STANDARD = "standard"


@dataclass(frozen=True)
class OfferedModel:
    # `key` doubles as the llmbroker paid-catalog alias.
    key: str
    title: str
    suffix: str
    provider: str | None
    default_effort: str | None = None
    default_tier: str | None = None


OFFERED_MODELS: dict[str, OfferedModel] = {
    model.key: model
    for model in (
        OfferedModel(POOL, "Free pool", "free", None),
        OfferedModel("gpt", "GPT-5.6 Sol", "Sol", OPENAI, EFFORT_NONE, TIER_PRIORITY),
        OfferedModel("gpt-fast", "GPT-5.6 Luna", "Luna", OPENAI, "low", TIER_PRIORITY),
        OfferedModel("opus", "Claude Opus", "Opus", ANTHROPIC, "low"),
    )
}

EFFORTS: dict[str, tuple[str, ...]] = {
    OPENAI: (EFFORT_NONE, "low", "medium", "high"),
    ANTHROPIC: (EFFORT_NONE, "low", "medium", "high"),
}

TIERS: dict[str, tuple[str, ...]] = {
    OPENAI: (TIER_PRIORITY, TIER_STANDARD),
}

DEFAULT_AI_MODEL = "gpt"


def _offered(model: str) -> OfferedModel:
    try:
        return OFFERED_MODELS[model]
    except KeyError:
        raise ValueError(f"Model `{model}` is not offered") from None


def efforts_of(model: str) -> tuple[str, ...]:
    provider = _offered(model).provider
    return EFFORTS.get(provider, ()) if provider else ()


def tiers_of(model: str) -> tuple[str, ...]:
    provider = _offered(model).provider
    return TIERS.get(provider, ()) if provider else ()


def default_knobs(model: str) -> dict[str, str]:
    offered = _offered(model)
    knobs = {}
    if offered.default_effort:
        knobs["effort"] = offered.default_effort
    if offered.default_tier:
        knobs["tier"] = offered.default_tier
    return knobs


def validate_knobs(model: str, effort: str | None = None, tier: str | None = None) -> None:
    _offered(model)
    if effort and effort not in efforts_of(model):
        raise ValueError(f"Reasoning effort `{effort}` is not available for model `{model}`")
    if tier and tier not in tiers_of(model):
        raise ValueError(f"Processing tier `{tier}` is not available for model `{model}`")


def request_params(
    model: str,
    effort: str | None = None,
    tier: str | None = None,
) -> dict[str, Any]:
    # Only what echo-words measured is ever sent; anything else stays the model default.
    validate_knobs(model, effort, tier)
    provider = _offered(model).provider
    params: dict[str, Any] = {}
    if effort:
        if provider == ANTHROPIC and effort == EFFORT_NONE:
            params["thinking"] = {"type": "disabled"}
        else:
            params["reasoning_effort"] = effort
    if tier == TIER_PRIORITY:
        params["service_tier"] = TIER_PRIORITY
    return params


@lru_cache(maxsize=1)
def _catalog_providers() -> dict[str, str]:
    return {
        row.alias: row.provider.id
        for row in curated_paid(home=settings.LLMBROKER_HOME)
        if row.alias
    }


def provider_of(model: str) -> str | None:
    return _catalog_providers().get(model)


def is_available(model: str) -> bool:
    # A paid option lasts only while the installed catalog still carries its alias.
    offered = OFFERED_MODELS.get(model)
    if offered is None:
        return False
    if offered.provider is None:
        return True
    return provider_of(model) == offered.provider


def editor_models() -> list[dict[str, Any]]:
    return [
        {
            "key": model.key,
            "title": model.title,
            "suffix": model.suffix,
            "provider": model.provider,
            "efforts": list(efforts_of(model.key)),
            "tiers": list(tiers_of(model.key)),
            "defaults": default_knobs(model.key),
        }
        for model in OFFERED_MODELS.values()
        if is_available(model.key)
    ]
