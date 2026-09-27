import asyncio
import atexit
import logging
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import llmbroker
from django.conf import settings
from django.db import connections
from llmbroker.standalone.secrets import parse_env_file

from lexiflux.language import key_store
from lexiflux.language.ai_models import OFFERED_MODELS

logger = logging.getLogger(__name__)

# As the race's second lane these cannot rescue a Gemini stall (Nemotron holds the lane
# without text, Laguna is mostly rate-limited), so the stall ended in "busy".
EXCLUDED_POOL_LLMS = ("openrouter-nemotron-3-ultra", "openrouter-laguna-s-2.1")

_lock = threading.Lock()
_broker: "RebuildableBroker | None" = None
_exclusions_applied = False


def env_file() -> Path:
    return Path(settings.BASE_DIR) / ".env"


def server_refs() -> frozenset[str]:
    # What llmbroker.Secrets resolves: the environment, then .env, a blank value counting as unset.
    names = {name for name, value in os.environ.items() if value.strip()}
    try:
        values = parse_env_file(env_file().read_text(encoding="utf-8"))
    except OSError:
        values = {}
    names |= {name for name, value in values.items() if value.strip()}
    return frozenset(names)


def _outside_requests(call: Callable[..., Any], *args: Any) -> Any:
    try:
        return call(*args)
    finally:
        # The broker's worker threads never finish a request, where Django closes connections.
        connections.close_all()


class KeySecrets:
    """A user's own keys from lexiflux's database; the server's from the environment and .env."""

    def __init__(self, env: Path) -> None:
        self._server = llmbroker.Secrets(env)

    async def resolve(self, ref: str) -> str:
        scope, _, shared_ref = ref.rpartition("/")
        if not scope:
            return await self._server.resolve(ref)
        user_id = key_store.user_of(scope)
        value = None
        if user_id is not None:
            value = await asyncio.to_thread(
                _outside_requests,
                key_store.own_key,
                user_id,
                shared_ref,
            )
        if value is None:
            raise KeyError(f"no readable key for {ref!r}")
        return value

    async def refs(self, prefix: str = "") -> frozenset[str]:
        own = await asyncio.to_thread(_outside_requests, key_store.scoped_refs)
        return frozenset(ref for ref in own | server_refs() if ref.startswith(prefix))


class RebuildableBroker(llmbroker.Broker):
    def rebuild(self) -> None:
        # AsyncBroker.rebuild is public; the synchronous façade does not pass it through.
        self._run(self._async.rebuild())


def direct_aliases() -> list[str]:
    return [model.key for model in OFFERED_MODELS.values() if model.provider]


def pool_keys() -> dict[str, Any]:
    pool = llmbroker.curated_pool(home=settings.LLMBROKER_HOME)
    serving = {entry.api_key_ref for entry in pool.configs if entry.name not in EXCLUDED_POOL_LLMS}
    return {ref: info for ref, info in pool.keys.items() if ref in serving}


def exclude_pool_llms(broker: llmbroker.Broker) -> None:
    pool = broker.snapshot()
    for name in EXCLUDED_POOL_LLMS:
        entry = pool.get(name)
        if entry is None:
            logger.warning("Pool model %s to exclude is not in the llmbroker catalog", name)
        elif not entry.disabled:
            broker.disable_llm(name)


def get_broker() -> llmbroker.Broker:
    global _broker, _exclusions_applied  # noqa: PLW0603
    with _lock:
        if _broker is None:
            _broker = RebuildableBroker(
                settings.LLMBROKER_DATASOURCE,
                secrets=KeySecrets(env_file()),
                direct=direct_aliases(),
                home=settings.LLMBROKER_HOME,
            )
            atexit.register(_broker.close)
            _exclusions_applied = False
        if not _exclusions_applied:
            exclude_pool_llms(_broker)
            _exclusions_applied = True
        return _broker


def refresh_keys() -> None:
    # A caller holds its keys until the broker rebuilds; a broker not built yet holds none.
    current = _broker
    if current is None:
        return
    try:
        current.rebuild()
    except Exception:
        logger.exception("Could not re-read the AI keys; the change applies at the next rebuild")


def llms_for(user: Any) -> llmbroker.LLMs:
    return get_broker().for_scope(key_store.scope_of(user.id))
