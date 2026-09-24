# The rest of the suite fakes llmbroker. Here lexiflux's article calls drive the installed
# llmbroker itself; only provider HTTP and the curated-list fetch are faked.

import io
import json
import os
import urllib.error
import urllib.request
import warnings
from collections import Counter
from dataclasses import dataclass
from email.message import Message
from importlib import resources
from types import SimpleNamespace
from unittest.mock import patch

import allure
import httpx
import llmbroker
import pytest

from lexiflux.language import broker as lexiflux_broker
from lexiflux.language.ai_models import OFFERED_MODELS, POOL, default_knobs
from lexiflux.language.llm import ArticleError, ArticleRequest, stream_article

# Taken at import, before the suite-wide guard replaces it for each test.
REAL_GET_BROKER = lexiflux_broker.get_broker

CURATED_HOST = "https://raw.githubusercontent.com/"
USAGE = {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}


@dataclass(frozen=True)
class Sent:
    host: str
    model: str
    stream: bool
    authorization: str
    body: dict


def fake_key(ref: str) -> str:
    return f"fake-{ref.lower()}"


def sse(deltas: tuple[str, ...]) -> bytes:
    chunks = [{"choices": [{"index": 0, "delta": {"content": delta}}]} for delta in deltas]
    chunks.append({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
    chunks.append({"choices": [], "usage": USAGE})
    lines = [f"data: {json.dumps(chunk)}\n\n" for chunk in chunks]
    return ("".join(lines) + "data: [DONE]\n\n").encode()


class Wire:
    def __init__(self) -> None:
        self.replies: dict[str, tuple[str, ...]] = {}
        self.sent: list[Sent] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions"), request.url
        body = json.loads(request.content)
        stream = bool(body.get("stream"))
        self.sent.append(
            Sent(
                request.url.host,
                body["model"],
                stream,
                request.headers.get("authorization", ""),
                body,
            ),
        )
        deltas = self.replies.get(body["model"], (f"{body['model']} ", "answers"))
        if stream:
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=sse(deltas),
            )
        message = {"role": "assistant", "content": "".join(deltas)}
        return httpx.Response(
            200,
            json={
                "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
                "usage": USAGE,
            },
        )

    def urlopen(self, url: object, timeout: float | None = None) -> io.BytesIO:
        target = url if isinstance(url, str) else url.full_url  # type: ignore[attr-defined]
        assert target.startswith(CURATED_HOST), target
        bundled = resources.files("llmbroker").joinpath("presets", target.rsplit("/", 1)[-1])
        if not bundled.is_file():
            raise urllib.error.HTTPError(target, 404, "Not Found", Message(), None)
        return io.BytesIO(bundled.read_bytes())


@pytest.fixture
def curated_refs() -> set[str]:
    refs = set(llmbroker.curated_pool().keys)
    refs |= {model.provider.api_key_ref for model in llmbroker.curated_paid()}
    return refs


@pytest.fixture
def wire(monkeypatch, tmp_path, settings, curated_refs):
    wire = Wire()
    for name in {*curated_refs, *(name for name in os.environ if name.endswith("_API_KEY"))}:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLMBROKER_HOME", str(tmp_path / "llmbroker"))
    settings.LLMBROKER_HOME = tmp_path / "llmbroker"
    # The broker's .env is the repo's; pointing BASE_DIR away keeps the real keys out.
    settings.BASE_DIR = tmp_path
    settings.LLMBROKER_DATASOURCE = None
    monkeypatch.setattr(lexiflux_broker, "_broker", None)

    build_async = httpx.AsyncClient.__init__
    build_sync = httpx.Client.__init__

    def mocked_async(client, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(wire.handle)
        build_async(client, *args, **kwargs)

    def mocked_sync(client, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(wire.handle)
        build_sync(client, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", mocked_async)
    monkeypatch.setattr(httpx.Client, "__init__", mocked_sync)
    monkeypatch.setattr(urllib.request, "urlopen", wire.urlopen)
    # Undoes the suite-wide guard for this module only: here the broker is real and offline.
    with (
        patch("lexiflux.language.llm.llms_for", lexiflux_broker.llms_for),
        patch("lexiflux.language.broker.get_broker", REAL_GET_BROKER),
    ):
        yield wire
    if lexiflux_broker._broker is not None:
        lexiflux_broker._broker.close()


@pytest.fixture
def pay(monkeypatch):
    def pay(*refs: str) -> None:
        for ref in refs:
            monkeypatch.setenv(ref, fake_key(ref))

    return pay


@pytest.fixture
def lone_pool_entry() -> llmbroker.LLMConfig:
    # A key that pays for exactly one pool entry, so the race has one lane and no replacement.
    configs = llmbroker.curated_pool().configs
    per_ref = Counter(entry.api_key_ref for entry in configs)
    return next(entry for entry in configs if per_ref[entry.api_key_ref] == 1)


def article(model: str, article_type: str = "AI dictionary") -> ArticleRequest:
    knobs = default_knobs(model) if model != POOL else {}
    return ArticleRequest(
        article_type=article_type,
        model=model,
        effort=knobs.get("effort"),
        tier=knobs.get("tier"),
        prompt=None,
        word="made out",
        sentence="She made out the shape of a ship through the fog.",
        text_language="English",
        user_language="Serbian",
        user=SimpleNamespace(id=7),
    )


def paid(alias: str) -> llmbroker.CuratedModel:
    return next(model for model in llmbroker.curated_paid() if model.alias == alias)


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_the_catalog_carries_every_offered_paid_model_with_its_provider():
    catalog = {model.alias: model.provider.id for model in llmbroker.curated_paid()}
    offered = {key: model.provider for key, model in OFFERED_MODELS.items() if model.provider}

    assert offered == {"gpt": "openai", "gpt-fast": "openai", "opus": "anthropic"}
    assert {alias: catalog.get(alias) for alias in offered} == offered


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_every_pool_key_and_every_paid_provider_has_help():
    keys = llmbroker.curated_pool().keys

    assert keys
    assert all(info.help.strip() for info in keys.values())
    assert all(paid(alias).provider.key_help.strip() for alias in ("gpt", "gpt-fast", "opus"))


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_sync_stream_exists_on_the_scoped_llms_and_the_direct_client():
    assert callable(llmbroker.LLMs.stream)
    assert callable(llmbroker.DirectClient.stream)
    assert callable(llmbroker.Broker.for_scope)
    assert callable(llmbroker.LLMs.direct)


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_a_pool_article_streams_from_the_pool_on_its_key(wire, pay, lone_pool_entry):
    pay(lone_pool_entry.api_key_ref)
    wire.replies[lone_pool_entry.model] = ("**made out** ", "razabrati")

    events = [event.to_dict() for event in stream_article(article(POOL))]

    assert events == [
        {"event": "delta", "text": "**made out** "},
        {"event": "delta", "text": "razabrati"},
    ]
    assert [(sent.model, sent.stream, sent.authorization) for sent in wire.sent] == [
        (lone_pool_entry.model, True, f"Bearer {fake_key(lone_pool_entry.api_key_ref)}"),
    ]
    prompt = json.dumps(wire.sent[0].body["messages"], ensure_ascii=False)
    assert "made out" in prompt
    assert "She made out the shape of a ship through the fog." in prompt
    assert "Serbian" in prompt


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_a_paid_article_streams_from_its_catalog_model_with_its_knobs(wire, pay):
    sol = paid("gpt")
    pay(sol.provider.api_key_ref)
    wire.replies[sol.model] = ("In ", "depth")

    events = [event.to_dict() for event in stream_article(article("gpt", "In depth"))]

    assert [event["text"] for event in events] == ["In ", "depth"]
    (sent,) = wire.sent
    assert (sent.host, sent.model, sent.stream) == (
        httpx.URL(sol.provider.base_url).host,
        sol.model,
        True,
    )
    assert sent.authorization == f"Bearer {fake_key(sol.provider.api_key_ref)}"
    assert sent.body["reasoning_effort"] == "none"
    assert sent.body["service_tier"] == "priority"


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_anthropic_effort_none_disables_thinking(wire, pay):
    opus = paid("opus")
    pay(opus.provider.api_key_ref)
    request = article("opus")
    request = ArticleRequest(**{**request.__dict__, "effort": "none"})

    list(stream_article(request))

    (sent,) = wire.sent
    assert sent.model == opus.model
    assert sent.body["thinking"] == {"type": "disabled"}
    assert "service_tier" not in sent.body


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_a_pool_without_keys_shows_the_no_key_message_and_sends_nothing(wire):
    (event,) = [event.to_dict() for event in stream_article(article(POOL))]

    assert (event["event"], event["kind"]) == ("error", ArticleError.NO_KEYS)
    assert lexiflux_broker.pool_keys()
    for ref in llmbroker.curated_pool().keys:
        assert (ref in event["html"]) == (ref in lexiflux_broker.pool_keys())
    assert wire.sent == []


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_the_excluded_pool_models_are_still_in_the_catalog():
    # A dropped name only warns: the exclusion is then a no-op, but a renamed model
    # would be back in the race, so look at the catalog's names when this fires.
    catalog = {entry.name for entry in llmbroker.curated_pool().configs}
    missing = [name for name in lexiflux_broker.EXCLUDED_POOL_LLMS if name not in catalog]
    if missing:
        warnings.warn(
            f"excluded pool models no longer in the llmbroker catalog: {missing}; "
            f"catalog: {sorted(catalog)}",
            stacklevel=1,
        )


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_excluded_pool_models_are_disabled_and_never_raced(wire, pay):
    pay("GROQ_API_KEY", "OPENROUTER_API_KEY")

    events = [event.to_dict() for event in stream_article(article(POOL))]

    assert events and all(event["event"] == "delta" for event in events)
    assert wire.sent
    assert not {sent.model for sent in wire.sent} & {
        entry.model
        for entry in llmbroker.curated_pool().configs
        if entry.name in lexiflux_broker.EXCLUDED_POOL_LLMS
    }
    snapshot = lexiflux_broker.get_broker().snapshot()
    assert snapshot["openrouter-nemotron-3-ultra"].disabled
    assert snapshot["openrouter-laguna-s-2.1"].disabled
    assert not snapshot["groq-gpt-oss-120b"].disabled


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_a_key_that_serves_only_excluded_models_shows_the_no_key_message(wire, pay):
    pay("OPENROUTER_API_KEY")

    (event,) = [event.to_dict() for event in stream_article(article(POOL))]

    assert (event["event"], event["kind"]) == ("error", ArticleError.NO_KEYS)
    assert "OPENROUTER_API_KEY" not in event["html"]
    assert "GROQ_API_KEY" in event["html"]
    assert wire.sent == []


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_an_excluded_name_unknown_to_the_catalog_does_not_break_the_pool(wire, pay):
    entry = next(e for e in llmbroker.curated_pool().configs if e.api_key_ref == "GROQ_API_KEY")
    pay("GROQ_API_KEY")
    with patch.object(lexiflux_broker, "EXCLUDED_POOL_LLMS", ("no-such-llm",)):
        events = [event.to_dict() for event in stream_article(article(POOL))]

    assert events and all(event["event"] == "delta" for event in events)
    assert {sent.model for sent in wire.sent} == {entry.model}
    assert "no-such-llm" not in lexiflux_broker.get_broker().snapshot()


@allure.epic("AI articles")
@allure.feature("llmbroker contract")
def test_a_paid_model_without_its_key_names_the_key_and_sends_nothing(wire):
    (event,) = [event.to_dict() for event in stream_article(article("gpt"))]

    assert (event["event"], event["kind"]) == ("error", ArticleError.MISSING_KEY)
    assert paid("gpt").provider.api_key_ref in event["html"]
    assert wire.sent == []
