from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import allure
import httpx
import pytest
from llmbroker import (
    AuthError,
    LLMTimeoutError,
    MissingKeyError,
    NoLLMAvailableError,
    ProviderError,
    RateLimitError,
    StreamInterruptedError,
    StreamReplacementError,
    UnknownModelError,
)

from lexiflux.language import llm
from lexiflux.language.llm import (
    ArticleError,
    ArticleEvent,
    ArticleRequest,
    build_prompt,
    generate_article,
    stream_article,
)


class FakeStream:
    def __init__(self, script):
        self.script = list(script)
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.closed or not self.script:
            raise StopIteration
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class FakeDirectClient:
    def __init__(self, script, answer):
        self.script = script
        self.answer = answer
        self.closed = False
        self.stream_closed = False
        self.calls = []

    def stream(self, prompt=None, *, messages=None, timeout=None, params=None):
        self.calls.append({"prompt": prompt, "messages": messages, "params": params})
        try:
            for item in self.script:
                if isinstance(item, BaseException):
                    raise item
                yield item
        finally:
            self.stream_closed = True

    def ask(self, prompt=None, *, messages=None, timeout=None, params=None):
        self.calls.append({"prompt": prompt, "messages": messages, "params": params})
        if isinstance(self.answer, BaseException):
            raise self.answer
        return SimpleNamespace(text=self.answer)

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class FakeLLMs:
    def __init__(self, script=(), answer="whole answer", direct_error=None):
        self.script = list(script)
        self.answer = answer
        self.direct_error = direct_error
        self.streams = []
        self.clients = []
        self.calls = []

    def stream(self, prompt, **kwargs):
        self.calls.append(("stream", prompt, kwargs))
        stream = FakeStream(self.script)
        self.streams.append(stream)
        return stream

    def ask(self, prompt, **kwargs):
        self.calls.append(("ask", prompt, kwargs))
        if isinstance(self.answer, BaseException):
            raise self.answer
        return SimpleNamespace(text=self.answer)

    def direct(self, model):
        self.calls.append(("direct", model, {}))
        if self.direct_error is not None:
            raise self.direct_error
        client = FakeDirectClient(self.script, self.answer)
        self.clients.append(client)
        return client


@pytest.fixture(autouse=True)
def clean_cache():
    llm.clear_cache()
    yield
    llm.clear_cache()


@pytest.fixture
def fake():
    holder = {"llms": FakeLLMs()}
    with patch("lexiflux.language.llm.llms_for", side_effect=lambda user: holder["llms"]):
        yield holder


def make_request(**changes):
    req = ArticleRequest(
        article_type="AI dictionary",
        model="pool",
        effort=None,
        tier=None,
        prompt=None,
        word="made out",
        sentence="She made out a shape in the fog.",
        text_language="English",
        user_language="Serbian",
        user=SimpleNamespace(id=7),
    )
    return replace(req, **changes)


def direct_request(**changes):
    return make_request(
        **{"article_type": "In depth", "model": "gpt", "effort": "none", "tier": "priority"}
        | changes
    )


def events(req):
    return list(stream_article(req))


@allure.epic("AI articles")
@allure.feature("Prompts")
class TestPrompts:
    @pytest.mark.parametrize(
        "article_type",
        ["AI dictionary", "In depth", "Translate", "Explain", "Lexical", "Origin"],
    )
    def test_prompt_has_language_names_word_and_sentence(self, article_type):
        prompt = build_prompt(make_request(article_type=article_type))
        assert "English" in prompt
        assert "Serbian" in prompt
        assert "made out" in prompt
        assert "She made out a shape in the fog." in prompt
        for leftover in ("{", "}", "[HIGHLIGHT]", "[FRAGMENT]"):
            assert leftover not in prompt

    def test_sentence_prompt_takes_sentence_only(self):
        prompt = build_prompt(make_request(article_type="Sentence", word="zzz"))
        assert "She made out a shape in the fog." in prompt
        assert "zzz" not in prompt
        assert "Serbian" in prompt

    def test_custom_ai_on_pool_joins_prompt_and_input(self, fake):
        req = make_request(article_type="AI", prompt="Give synonyms in {user_language}.")
        events(req)
        prompt = fake["llms"].calls[0][1]
        assert prompt.startswith("Give synonyms in Serbian.")
        assert '"made out"' in prompt
        assert '"She made out a shape in the fog."' in prompt

    def test_custom_ai_on_direct_sends_system_and_user_messages(self, fake):
        fake["llms"] = FakeLLMs(script=["x"])
        events(direct_request(article_type="AI", prompt="Give synonyms."))
        call = fake["llms"].clients[0].calls[0]
        assert call["prompt"] is None
        assert call["messages"][0] == {"role": "system", "content": "Give synonyms."}
        assert call["messages"][1]["role"] == "user"
        assert '"made out"' in call["messages"][1]["content"]


@allure.epic("AI articles")
@allure.feature("Streaming")
class TestStreamArticle:
    def test_pool_deltas(self, fake):
        fake["llms"] = FakeLLMs(script=["Hel", "lo"])
        assert events(make_request()) == [ArticleEvent.delta("Hel"), ArticleEvent.delta("lo")]
        name, prompt, kwargs = fake["llms"].calls[0]
        assert name == "stream"
        assert kwargs == {"operation": "AI dictionary", "fastest_of": 2, "wait": 25}
        assert fake["llms"].streams[0].closed

    def test_direct_deltas_with_knob_params(self, fake):
        fake["llms"] = FakeLLMs(script=["a", "b"])
        assert events(direct_request()) == [ArticleEvent.delta("a"), ArticleEvent.delta("b")]
        assert fake["llms"].calls[0][:2] == ("direct", "gpt")
        client = fake["llms"].clients[0]
        assert client.calls[0]["params"] == {"reasoning_effort": "none", "service_tier": "priority"}
        assert "made out" in client.calls[0]["prompt"]
        assert client.closed
        assert client.stream_closed

    def test_replacement_replaces_whole_answer(self, fake):
        replacement = StreamReplacementError(
            "lost the race",
            replacement=SimpleNamespace(text="complete answer"),
            streamed_llm_name="slow",
        )
        fake["llms"] = FakeLLMs(script=["provis", replacement])
        assert events(make_request()) == [
            ArticleEvent.delta("provis"),
            ArticleEvent.replace("complete answer"),
        ]
        assert events(make_request()) == [ArticleEvent.delta("complete answer")]

    @pytest.mark.parametrize(
        "error",
        [
            StreamInterruptedError("died", llm_name="x"),
            LLMTimeoutError("wait ran out"),
            httpx.ReadError("connection reset"),
        ],
    )
    def test_error_after_text_keeps_text_and_says_cut_off(self, fake, error):
        fake["llms"] = FakeLLMs(script=["partial", error])
        result = events(make_request())
        assert result[0] == ArticleEvent.delta("partial")
        assert result[1].event == "error"
        assert result[1].kind == ArticleError.CUT_OFF
        assert "cut off" in result[1].html
        assert len(result) == 2

    def test_cut_off_answer_is_not_cached(self, fake):
        fake["llms"] = FakeLLMs(script=["partial", LLMTimeoutError("t")])
        events(make_request())
        fake["llms"] = FakeLLMs(script=["fresh"])
        assert events(make_request()) == [ArticleEvent.delta("fresh")]

    @pytest.mark.parametrize(
        "error, kind",
        [
            (LLMTimeoutError("wait ran out"), ArticleError.BUSY),
            (httpx.ConnectError("refused"), ArticleError.GENERIC),
            (NoLLMAvailableError("none", reason="no_keys"), ArticleError.NO_KEYS),
            (NoLLMAvailableError("none", reason="timeout"), ArticleError.BUSY),
        ],
    )
    def test_error_before_text(self, fake, error, kind):
        fake["llms"] = FakeLLMs(script=[error])
        result = events(make_request())
        assert len(result) == 1
        assert result[0].event == "error"
        assert result[0].kind == kind

    def test_direct_errors_at_direct(self, fake):
        fake["llms"] = FakeLLMs(direct_error=MissingKeyError("no key"))
        result = events(direct_request())
        assert result[0].kind == ArticleError.MISSING_KEY
        assert "OPENAI_API_KEY" in result[0].html

    def test_cache_hit_replays_one_delta(self, fake):
        fake["llms"] = FakeLLMs(script=["one ", "two ", "three"])
        events(make_request())
        fake["llms"] = FakeLLMs(script=["other"])
        assert events(make_request()) == [ArticleEvent.delta("one two three")]
        assert fake["llms"].calls == []

    def test_cache_key_includes_knobs_and_user(self, fake):
        fake["llms"] = FakeLLMs(script=["first"])
        events(direct_request())
        fake["llms"] = FakeLLMs(script=["second"])
        assert events(direct_request(tier="standard")) == [ArticleEvent.delta("second")]
        fake["llms"] = FakeLLMs(script=["third"])
        assert events(direct_request(user=SimpleNamespace(id=8))) == [ArticleEvent.delta("third")]

    def test_closing_early_closes_pool_stream(self, fake):
        fake["llms"] = FakeLLMs(script=["a", "b", "c"])
        gen = stream_article(make_request())
        assert next(gen) == ArticleEvent.delta("a")
        gen.close()
        assert fake["llms"].streams[0].closed

    def test_closing_early_closes_direct_client(self, fake):
        fake["llms"] = FakeLLMs(script=["a", "b", "c"])
        gen = stream_article(direct_request())
        assert next(gen) == ArticleEvent.delta("a")
        gen.close()
        client = fake["llms"].clients[0]
        assert client.stream_closed
        assert client.closed

    def test_early_close_is_not_cached(self, fake):
        fake["llms"] = FakeLLMs(script=["a", "b"])
        gen = stream_article(make_request())
        next(gen)
        gen.close()
        fake["llms"] = FakeLLMs(script=["fresh"])
        assert events(make_request()) == [ArticleEvent.delta("fresh")]

    def test_unknown_option_shows_retired_message(self, fake):
        result = events(make_request(model="claude-sonnet-4-0"))
        assert result[0].kind == ArticleError.RETIRED
        assert "claude-sonnet-4-0" in result[0].html
        assert fake["llms"].calls == []

    def test_dropped_catalog_alias_shows_retired_message(self, fake):
        with patch("lexiflux.language.ai_models._catalog_providers", return_value={}):
            result = events(direct_request())
        assert result[0].kind == ArticleError.RETIRED

    def test_event_dicts(self):
        assert ArticleEvent.delta("x").to_dict() == {"event": "delta", "text": "x"}
        assert ArticleEvent.replace("y").to_dict() == {"event": "replace", "text": "y"}
        assert ArticleEvent.error(ArticleError("busy", "<p>b</p>")).to_dict() == {
            "event": "error",
            "kind": "busy",
            "html": "<p>b</p>",
        }


@allure.epic("AI articles")
@allure.feature("Inline article")
class TestGenerateArticle:
    def test_pool_ask(self, fake):
        assert generate_article(make_request()) == "whole answer"
        name, _, kwargs = fake["llms"].calls[0]
        assert name == "ask"
        assert kwargs["operation"] == "AI dictionary"

    def test_direct_ask(self, fake):
        assert generate_article(direct_request()) == "whole answer"
        client = fake["llms"].clients[0]
        assert client.calls[0]["params"] == {"reasoning_effort": "none", "service_tier": "priority"}
        assert client.closed

    def test_cached(self, fake):
        generate_article(make_request())
        fake["llms"] = FakeLLMs(answer="other")
        assert generate_article(make_request()) == "whole answer"

    def test_error_raises_article_error(self, fake):
        fake["llms"] = FakeLLMs(answer=AuthError("rejected", status=401))
        with pytest.raises(ArticleError) as exc_info:
            generate_article(make_request(model="opus", article_type="Origin"))
        assert exc_info.value.kind == ArticleError.AUTH
        assert "Anthropic" in exc_info.value.html


@allure.epic("AI articles")
@allure.feature("Errors")
class TestErrorMessages:
    def error_for(self, exc, req=None, had_text=False):
        return llm.article_error(exc, req or make_request(), had_text=had_text)

    def test_no_keys_lists_pool_keys_with_links_and_env_vars(self):
        error = self.error_for(NoLLMAvailableError("none", reason="no_keys"))
        assert error.kind == ArticleError.NO_KEYS
        assert "The free pool needs at least one key" in error.html
        assert "GROQ_API_KEY" in error.html
        assert '<a href="https://console.groq.com/keys"' in error.html
        assert ".env" in error.html
        assert "ai-settings" not in error.html

    def test_no_keys_on_koyeb_points_to_server_environment(self):
        with patch("lexiflux.language.llm.keys_on_server", return_value=True):
            error = self.error_for(NoLLMAvailableError("none", reason="no_keys"))
        assert "environment variable of the server" in error.html
        assert ".env" not in error.html

    def test_busy_with_retry_at(self):
        retry_at = datetime.now(UTC) + timedelta(seconds=30)
        error = self.error_for(NoLLMAvailableError("none", reason="timeout", retry_at=retry_at))
        assert error.kind == ArticleError.BUSY
        assert "retry in 30 s" in error.html or "retry in 29 s" in error.html

    def test_no_keys_omits_keys_that_serve_only_excluded_pool_models(self):
        error = self.error_for(NoLLMAvailableError("none", reason="no_keys"))
        assert "OPENROUTER_API_KEY" not in error.html
        for ref in ("GROQ_API_KEY", "GEMINI_API_KEY", "ZAI_API_KEY"):
            assert ref in error.html

    def test_only_excluded_pool_models_payable_shows_the_no_keys_message(self):
        error = self.error_for(NoLLMAvailableError("none", reason="all_disabled"))
        assert error.kind == ArticleError.NO_KEYS
        assert "GROQ_API_KEY" in error.html
        assert "OPENROUTER_API_KEY" not in error.html

    def test_busy_without_retry_at(self):
        error = self.error_for(NoLLMAvailableError("none", reason="timeout"))
        assert error.kind == ArticleError.BUSY
        assert "retry in" not in error.html

    def test_missing_key(self):
        error = self.error_for(MissingKeyError("no key"), direct_request())
        assert error.kind == ArticleError.MISSING_KEY
        assert "OpenAI" in error.html
        assert "OPENAI_API_KEY" in error.html
        assert "platform.openai.com" in error.html

    def test_auth(self):
        error = self.error_for(AuthError("rejected", status=401), direct_request())
        assert error.kind == ArticleError.AUTH
        assert "Key rejected by OpenAI" in error.html

    def test_rate_limit_with_retry_after(self):
        error = self.error_for(
            RateLimitError("slow down", status=429, retry_after=12), direct_request()
        )
        assert error.kind == ArticleError.BUSY
        assert "retry in 12 s" in error.html

    def test_unknown_model(self):
        error = self.error_for(UnknownModelError("gone"), direct_request())
        assert error.kind == ArticleError.RETIRED
        assert "AI Model No Longer Available" in error.html

    def test_generic_shows_the_exception_type_and_logs_the_text(self, caplog):
        error = self.error_for(ProviderError("upstream exploded", status=500))
        assert error.kind == ArticleError.GENERIC
        assert "ProviderError" in error.html
        assert "upstream exploded" not in error.html
        logged = [r for r in caplog.records if r.levelname == "ERROR"]
        assert logged and "upstream exploded" in str(logged[-1].exc_info[1])

    @pytest.mark.parametrize(
        ("exc", "req"),
        [
            (NoLLMAvailableError("none", reason="no_keys"), None),
            (NoLLMAvailableError("none", reason="all_disabled"), None),
            (MissingKeyError("no key"), "direct"),
            (AuthError("rejected", status=401), "direct"),
            (UnknownModelError("gone"), "direct"),
            (ProviderError("upstream exploded", status=500), None),
        ],
    )
    def test_error_html_has_no_surrounding_whitespace(self, exc, req):
        # keep-line-breaks panels (white-space: pre-line) show it as blank lines.
        error = self.error_for(exc, direct_request() if req else None)
        assert error.html == error.html.strip()
        assert error.html.startswith("<div")

    def test_cut_off_html_has_no_surrounding_whitespace(self):
        error = self.error_for(StreamInterruptedError("died", llm_name="x"), had_text=True)
        assert error.kind == ArticleError.CUT_OFF
        assert error.html == error.html.strip()

    def test_markdown_links_escape_quotes(self):
        text = llm.markdown_links('[key](https://x.io/a"onmouseover="alert(1)) and "q"')
        assert '"onmouseover="' not in text
        assert "&quot;" in text
        assert text.startswith('<a href="https://x.io/a&quot;onmouseover=&quot;alert(1"')
