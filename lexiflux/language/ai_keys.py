import html
import re
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from llmbroker import curated_providers

from lexiflux.language import key_store
from lexiflux.language.ai_models import OFFERED_MODELS, is_available
from lexiflux.language.broker import pool_keys, server_refs

OWN = "own"
SERVER = "server"
NONE = "none"

# llmbroker's signup effort for a key, in plain words; values not listed here are not shown.
_EFFORT = {
    "oauth": "Sign in with your account",
    "signup": "Free signup",
    "verify": "Signup with a phone or card check",
    "console": "Set up in a cloud console",
    "waitlist": "Access after approval",
}
# A shorter key shows no characters: its last 4 would reveal most of it.
_MIN_LENGTH_FOR_LAST4 = 9

_LINK = re.compile(
    r"\[([^\]]+)\]\((https?://[^)\s]+)\)"
    r"|(https?://[^\s<>()\[\]]*[^\s<>()\[\].,;:!?])",
)


@dataclass(frozen=True)
class AIKeyInfo:
    ref: str
    name: str
    hint: str
    pool: bool
    effort: str = ""


def hint_html(text: str, link_class: str = "") -> str:
    class_attr = f' class="{link_class}"' if link_class else ""

    def link(match: re.Match[str]) -> str:
        label, url, bare = match.groups()
        url = url or bare
        return f'<a href="{url}" target="_blank" rel="noopener"{class_attr}>{label or url}</a>'

    return _LINK.sub(link, html.escape(text))


def _link_text(text: str) -> str:
    match = _LINK.search(text)
    return match.group(1) if match and match.group(1) else ""


def ai_keys() -> list[AIKeyInfo]:
    providers = {p.id: p for p in curated_providers(home=settings.LLMBROKER_HOME)}
    labels = {provider.api_key_ref: provider.label for provider in providers.values()}
    keys = [
        AIKeyInfo(
            ref=ref,
            name=labels.get(ref) or _link_text(info.help).capitalize() or ref,
            hint=info.help,
            pool=True,
            effort=_EFFORT.get(info.extra.get("effort", ""), ""),
        )
        for ref, info in pool_keys().items()
    ]
    offered = dict.fromkeys(
        model.provider
        for model in OFFERED_MODELS.values()
        if model.provider and is_available(model.key)
    )
    for provider_id in offered:
        provider = providers.get(provider_id)
        if provider is None or any(key.ref == provider.api_key_ref for key in keys):
            continue
        keys.append(
            AIKeyInfo(
                ref=provider.api_key_ref,
                name=provider.label or provider.id,
                hint=provider.key_help,
                pool=False,
            ),
        )
    return keys


def _last4(key: str) -> str:
    return key[-4:] if len(key) >= _MIN_LENGTH_FOR_LAST4 else ""


def key_rows(
    user_id: int,
    refs: set[str] | None = None,
    link_class: str = "",
) -> list[dict[str, Any]]:
    # Sent to the browser: whose each key is, and only the last 4 characters of the user's own.
    own = key_store.own_keys(user_id)
    server = server_refs()
    rows = []
    for key in ai_keys():
        if refs is not None and key.ref not in refs:
            continue
        source = OWN if key.ref in own else SERVER if key.ref in server else NONE
        rows.append(
            {
                "ref": key.ref,
                "name": key.name,
                "pool": key.pool,
                "hint_html": hint_html(key.hint, link_class),
                "effort": key.effort,
                "source": source,
                "last4": _last4(own[key.ref]) if source == OWN else "",
            },
        )
    return rows
