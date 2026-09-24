import html
import logging
import math
import re
import threading
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from django.conf import settings
from django.template.loader import render_to_string
from llmbroker import (
    AuthError,
    LLMTimeoutError,
    MissingKeyError,
    NoLLMAvailableError,
    RateLimitError,
    StreamInterruptedError,
    StreamReplacementError,
    UnknownModelError,
    curated_providers,
)

from lexiflux.language.ai_models import (
    OFFERED_MODELS,
    POOL,
    is_available,
    request_params,
)
from lexiflux.language.broker import llms_for, pool_keys

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "resources" / "prompts"

CUSTOM_AI_TYPE = "AI"
POOL_FASTEST_OF = 2
POOL_WAIT_SECONDS = 25
CACHE_SIZE = 1000


@dataclass(frozen=True)
class ArticleRequest:
    article_type: str
    model: str
    effort: str | None
    tier: str | None
    prompt: str | None
    word: str
    sentence: str
    text_language: str
    user_language: str
    user: Any = field(compare=False, hash=False)


@dataclass(frozen=True)
class ArticleEvent:
    event: str
    text: str = ""
    html: str = ""
    kind: str = ""

    @classmethod
    def delta(cls, text: str) -> "ArticleEvent":
        return cls("delta", text=text)

    @classmethod
    def replace(cls, text: str) -> "ArticleEvent":
        return cls("replace", text=text)

    @classmethod
    def error(cls, error: "ArticleError") -> "ArticleEvent":
        return cls("error", html=error.html, kind=error.kind)

    def to_dict(self) -> dict[str, str]:
        if self.event == "error":
            return {"event": self.event, "kind": self.kind, "html": self.html}
        return {"event": self.event, "text": self.text}


class ArticleError(Exception):
    NO_KEYS = "no_keys"
    BUSY = "busy"
    MISSING_KEY = "missing_key"
    AUTH = "auth"
    CUT_OFF = "cut_off"
    RETIRED = "retired"
    GENERIC = "generic"

    def __init__(self, kind: str, html: str) -> None:
        super().__init__(f"{kind}: {html}")
        self.kind = kind
        self.html = html


_cache: OrderedDict[tuple[Any, ...], str] = OrderedDict()
_cache_lock = threading.Lock()


def _cache_key(req: ArticleRequest) -> tuple[Any, ...]:
    return (
        req.user.id,
        req.article_type,
        req.prompt,
        req.model,
        req.effort,
        req.tier,
        req.word,
        req.sentence,
        req.text_language,
        req.user_language,
    )


def _cache_get(req: ArticleRequest) -> str | None:
    key = _cache_key(req)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    return None


def _cache_put(req: ArticleRequest, text: str) -> None:
    with _cache_lock:
        _cache[_cache_key(req)] = text
        _cache.move_to_end(_cache_key(req))
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


@lru_cache(maxsize=32)
def _template(article_type: str) -> str:
    path = PROMPTS_DIR / f"{article_type}.txt"
    if not path.is_file():
        raise ValueError(f"No prompt for the article type `{article_type}`")
    return path.read_text(encoding="utf-8").strip()


def _fill(template: str, req: ArticleRequest) -> str:
    # Plain replacement: a literal brace in a prompt must not break formatting.
    for name, value in (
        ("text_language", req.text_language),
        ("user_language", req.user_language),
        ("word", req.word),
        ("sentence", req.sentence),
    ):
        template = template.replace(f"{{{name}}}", value)
    return template


def _custom_input(req: ArticleRequest) -> str:
    return f'Selected word: "{req.word}"\nSentence: "{req.sentence}"'


def build_prompt(req: ArticleRequest) -> str:
    # The pool takes one prompt string, so a custom AI article joins its two messages here.
    if req.article_type == CUSTOM_AI_TYPE:
        return f"{_fill(req.prompt or '', req)}\n\n{_custom_input(req)}"
    return _fill(_template(req.article_type), req)


def build_messages(req: ArticleRequest) -> list[dict[str, str]] | None:
    if req.article_type != CUSTOM_AI_TYPE:
        return None
    return [
        {"role": "system", "content": _fill(req.prompt or "", req)},
        {"role": "user", "content": _custom_input(req)},
    ]


def _direct_call_args(req: ArticleRequest) -> dict[str, Any]:
    messages = build_messages(req)
    args: dict[str, Any] = {"params": request_params(req.model, req.effort, req.tier)}
    if messages is None:
        args["prompt"] = build_prompt(req)
    else:
        args["messages"] = messages
    return args


def _check_model(req: ArticleRequest) -> None:
    if not is_available(req.model):
        raise _render(ArticleError.RETIRED, model_name=req.model)


def stream_article(req: ArticleRequest) -> Iterator[ArticleEvent]:
    # Closing the generator early must close the provider call, hence the context managers.
    cached = _cache_get(req)
    if cached is not None:
        yield ArticleEvent.delta(cached)
        return

    parts: list[str] = []
    try:
        _check_model(req)
        if req.model == POOL:
            with llms_for(req.user).stream(
                build_prompt(req),
                operation=req.article_type,
                fastest_of=POOL_FASTEST_OF,
                wait=POOL_WAIT_SECONDS,
            ) as stream:
                for delta in stream:
                    parts.append(delta)
                    yield ArticleEvent.delta(delta)
        else:
            with (
                llms_for(req.user).direct(req.model) as client,
                closing(client.stream(**_direct_call_args(req))) as deltas,  # type: ignore[type-var]
            ):
                for delta in deltas:
                    parts.append(delta)
                    yield ArticleEvent.delta(delta)
    except StreamReplacementError as exc:
        text = exc.replacement.text or ""
        parts = [text]
        yield ArticleEvent.replace(text)
    except ArticleError as exc:
        yield ArticleEvent.error(exc)
        return
    except Exception as exc:  # noqa: BLE001
        yield ArticleEvent.error(article_error(exc, req, had_text=bool(parts)))
        return
    _cache_put(req, "".join(parts))


def generate_article(req: ArticleRequest) -> str:
    cached = _cache_get(req)
    if cached is not None:
        return cached
    _check_model(req)
    try:
        if req.model == POOL:
            text = (
                llms_for(req.user)
                .ask(
                    build_prompt(req),
                    operation=req.article_type,
                    fastest_of=POOL_FASTEST_OF,
                    wait=POOL_WAIT_SECONDS,
                )
                .text
            )
        else:
            with llms_for(req.user).direct(req.model) as client:
                text = client.ask(**_direct_call_args(req)).text
    except Exception as exc:
        raise article_error(exc, req, had_text=False) from exc
    text = text or ""
    _cache_put(req, text)
    return text


def _render(kind: str, **context: Any) -> ArticleError:
    return ArticleError(kind, render_to_string("llm-error.html", {"kind": kind, **context}).strip())


_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def markdown_links(text: str) -> str:
    return _MARKDOWN_LINK.sub(
        r'<a href="\2" target="_blank" rel="noopener" class="alert-link">\1</a>',
        html.escape(text),
    )


def keys_on_server() -> bool:
    return getattr(settings, "LEXIFLUX_ENVIRONMENT", "") == "koyeb"


def _seconds_until(moment: datetime | None) -> int | None:
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    seconds = math.ceil((moment - datetime.now(UTC)).total_seconds())
    return seconds if seconds > 0 else None


def _provider(req: ArticleRequest) -> Any:
    offered = OFFERED_MODELS.get(req.model)
    provider_id = offered.provider if offered else None
    return next(
        (p for p in curated_providers(home=settings.LLMBROKER_HOME) if p.id == provider_id),
        None,
    )


def _busy(retry_in: int | None) -> ArticleError:
    return _render(ArticleError.BUSY, retry_in=retry_in)


def article_error(  # noqa: PLR0911
    exc: BaseException,
    req: ArticleRequest,
    *,
    had_text: bool,
) -> ArticleError:
    logger.warning(
        "AI article failed: %s model=%s type=%s",
        repr(exc),
        req.model,
        req.article_type,
    )
    if isinstance(exc, ArticleError):
        return exc
    if had_text and isinstance(
        exc,
        (StreamInterruptedError, LLMTimeoutError, httpx.TransportError),
    ):
        return _render(ArticleError.CUT_OFF)
    if isinstance(exc, NoLLMAvailableError):
        # "all_disabled" here means only keys of excluded pool models are set.
        if exc.reason in ("no_keys", "all_disabled"):
            keys = [
                {"env_var": ref, "help_html": markdown_links(info.help)}
                for ref, info in pool_keys().items()
            ]
            return _render(ArticleError.NO_KEYS, keys=keys, on_server=keys_on_server())
        return _busy(_seconds_until(exc.retry_at))
    if isinstance(exc, MissingKeyError):
        provider = _provider(req)
        return _render(
            ArticleError.MISSING_KEY,
            provider_label=provider.label if provider else req.model,
            key_help_html=markdown_links(provider.key_help) if provider else "",
            env_var=provider.api_key_ref if provider else "",
            on_server=keys_on_server(),
        )
    if isinstance(exc, AuthError):
        provider = _provider(req)
        return _render(ArticleError.AUTH, provider_label=provider.label if provider else req.model)
    if isinstance(exc, RateLimitError):
        return _busy(exc.retry_after if exc.retry_after and exc.retry_after > 0 else None)
    if isinstance(exc, LLMTimeoutError):
        return _busy(None)
    if isinstance(exc, UnknownModelError):
        return _render(ArticleError.RETIRED, model_name=req.model)
    # The exception text may carry secrets (a datasource URL), so users see only its type.
    logger.error("AI article failed with an unexpected error", exc_info=exc)
    return _render(ArticleError.GENERIC, model_name=req.model, error_type=type(exc).__name__)
