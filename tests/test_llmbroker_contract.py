# The rest of the suite fakes llmbroker. Here lexiflux's article calls drive the installed
# llmbroker itself; only provider HTTP and the curated-list fetch are faked.

import io
import json
import logging
import os
import re
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
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from lexiflux.language import broker as lexiflux_broker
from lexiflux.language.ai_models import OFFERED_MODELS, POOL, default_knobs
from lexiflux.language.llm import ArticleError, ArticleRequest, stream_article
from lexiflux.models import AIKey

# llmbroker reads a user's own keys from lexiflux's database in its own threads.
pytestmark = pytest.mark.django_db(transaction=True)

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
        self.refused: set[str] = set()

    def authorizations(self) -> list[str]:
        return [sent.authorization for sent in self.sent]

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
        if request.headers.get("authorization", "").removeprefix("Bearer ") in self.refused:
            return httpx.Response(401, json={"error": {"message": "Incorrect API key provided"}})
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


def article(
    model: str,
    article_type: str = "AI dictionary",
    user: object = None,
    word: str = "made out",
) -> ArticleRequest:
    knobs = default_knobs(model) if model != POOL else {}
    return ArticleRequest(
        article_type=article_type,
        model=model,
        effort=knobs.get("effort"),
        tier=knobs.get("tier"),
        prompt=None,
        word=word,
        sentence=f"She {word} the shape of a ship through the fog.",
        text_language="English",
        user_language="Serbian",
        user=user or SimpleNamespace(id=7),
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
    assert "You have no free pool key of your own, and the server has none." in event["html"]
    assert lexiflux_broker.pool_keys()
    for ref, info in llmbroker.curated_pool().keys.items():
        (link,) = re.findall(r"\]\((https?://[^)]+)\)", info.help)
        assert (link in event["html"]) == (ref in lexiflux_broker.pool_keys())
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
    assert "openrouter.ai" not in event["html"]
    assert "<strong>Groq</strong>" in event["html"]
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
    assert f"{paid('gpt').provider.label} needs an API key" in event["html"]
    assert reverse("ai-keys") in event["html"]
    assert wire.sent == []


@pytest.fixture
def people():
    make = get_user_model().objects.create_user
    return SimpleNamespace(
        alice=make(username="alice", email="alice@example.com", password="x"),
        bob=make(username="bob", email="bob@example.com", password="x"),
    )


class KeysPage:
    def __init__(self, user) -> None:
        self.client = Client()
        self.client.force_login(user)

    def save(self, ref: str, value: str) -> None:
        response = self.client.post(
            reverse("ai_key_api", args=[ref]),
            data=json.dumps({"key": value}),
            content_type="application/json",
        )
        assert response.status_code == 200, response.content

    def clear(self, ref: str) -> None:
        assert self.client.delete(reverse("ai_key_api", args=[ref])).status_code == 200


def run(request: ArticleRequest) -> list[dict]:
    return [event.to_dict() for event in stream_article(request)]


@allure.epic("AI keys")
@allure.feature("llmbroker contract")
def test_a_users_own_pool_key_pays_for_their_call_and_others_use_the_servers(
    wire, pay, lone_pool_entry, people
):
    ref = lone_pool_entry.api_key_ref
    pay(ref)
    KeysPage(people.alice).save(ref, "alice-own-pool-key")

    assert run(article(POOL, user=people.alice))[0]["event"] == "delta"
    assert run(article(POOL, user=people.bob))[0]["event"] == "delta"

    assert wire.authorizations() == ["Bearer alice-own-pool-key", f"Bearer {fake_key(ref)}"]


@allure.epic("AI keys")
@allure.feature("llmbroker contract")
def test_a_saved_or_cleared_key_takes_effect_on_the_next_call(wire, pay, people):
    ref = paid("gpt").provider.api_key_ref
    pay(ref)
    page = KeysPage(people.alice)

    run(article("gpt", user=people.alice, word="made out"))
    page.save(ref, "alice-own-openai-key")
    run(article("gpt", user=people.alice, word="made up"))
    run(article("gpt", user=people.bob, word="made up"))
    page.clear(ref)
    run(article("gpt", user=people.alice, word="made off"))

    assert wire.authorizations() == [
        f"Bearer {fake_key(ref)}",
        "Bearer alice-own-openai-key",
        f"Bearer {fake_key(ref)}",
        f"Bearer {fake_key(ref)}",
    ]


@allure.epic("AI keys")
@allure.feature("llmbroker contract")
def test_a_refused_own_pool_key_is_named_and_a_replacement_is_used(wire, lone_pool_entry, people):
    ref = lone_pool_entry.api_key_ref
    page = KeysPage(people.alice)
    page.save(ref, "alice-dead-key")
    wire.refused.add("alice-dead-key")

    # The call that meets the refusal only learns that no pool model answered; the key is
    # withdrawn then, so the next call says whose it was.
    (busy,) = run(article(POOL, user=people.alice))
    (error,) = run(article(POOL, user=people.alice, word="made off"))
    page.save(ref, "alice-fresh-key")
    answer = run(article(POOL, user=people.alice, word="made up"))

    assert busy["kind"] == ArticleError.BUSY
    assert error["kind"] == ArticleError.NO_KEYS
    assert "was refused by" in error["html"]
    assert "Your " in error["html"]
    assert reverse("ai-keys") in error["html"]
    assert answer[0]["event"] == "delta"
    assert wire.authorizations()[-1] == "Bearer alice-fresh-key"


@allure.epic("AI keys")
@allure.feature("llmbroker contract")
def test_a_refused_key_on_a_paid_model_names_whose_key_it_was(wire, pay, people):
    sol = paid("gpt")
    ref = sol.provider.api_key_ref
    pay(ref)
    wire.refused.add(fake_key(ref))
    page = KeysPage(people.alice)
    page.save(ref, "alice-dead-key")
    wire.refused.add("alice-dead-key")

    (own,) = run(article("gpt", user=people.alice))
    (server,) = run(article("gpt", user=people.bob))
    page.save(ref, "alice-fresh-key")
    fresh = run(article("gpt", user=people.alice, word="made up"))

    label = sol.provider.label
    assert own["kind"] == server["kind"] == ArticleError.AUTH
    assert f"Your {label} key was sent and {label} refused it." in own["html"]
    assert f"The server's {label} key was sent and {label} refused it." in server["html"]
    assert reverse("ai-keys") in own["html"]
    assert reverse("ai-keys") in server["html"]
    assert [event["event"] for event in fresh] == ["delta", "delta"]
    assert wire.authorizations()[-1] == "Bearer alice-fresh-key"


@allure.epic("AI keys")
@allure.feature("llmbroker contract")
def test_an_undecryptable_own_key_counts_as_not_set(wire, pay, people, settings):
    ref = paid("gpt").provider.api_key_ref
    pay(ref)
    KeysPage(people.alice).save(ref, "alice-own-openai-key")
    settings.SECRET_KEY = "rotated-secret-key"

    run(article("gpt", user=people.alice))

    assert wire.authorizations() == [f"Bearer {fake_key(ref)}"]


@allure.epic("AI keys")
@allure.feature("llmbroker contract")
def test_keys_never_appear_in_logs_or_pages(wire, pay, lone_pool_entry, people, caplog):
    caplog.set_level(logging.DEBUG)
    pool_ref = lone_pool_entry.api_key_ref
    paid_ref = paid("gpt").provider.api_key_ref
    pay(pool_ref)
    secrets = ["alice-pool-key-0001", "alice-dead-key-0002", fake_key(pool_ref)]
    page = KeysPage(people.alice)
    page.save(pool_ref, secrets[0])
    page.save(paid_ref, secrets[1])
    wire.refused.add(secrets[1])

    events = run(article(POOL, user=people.alice))
    events += run(article("gpt", user=people.alice))
    events += run(article(POOL, user=people.bob, word="made up"))
    html = page.client.get(reverse("ai-keys")).content.decode()

    assert [event["event"] for event in events] == ["delta", "delta", "error", "delta", "delta"]
    assert "0001" in html
    assert "0002" in html
    assert AIKey.objects.count() == 2
    for secret in secrets:
        assert secret not in caplog.text
        assert secret not in html
        assert secret not in json.dumps(events)
