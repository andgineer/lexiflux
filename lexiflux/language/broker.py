import atexit
import logging
import threading
from pathlib import Path
from typing import Any

import llmbroker
from django.conf import settings

from lexiflux.language.ai_models import OFFERED_MODELS

logger = logging.getLogger(__name__)

# As the race's second lane these cannot rescue a Gemini stall (Nemotron holds the lane
# without text, Laguna is mostly rate-limited), so the stall ended in "busy".
EXCLUDED_POOL_LLMS = ("openrouter-nemotron-3-ultra", "openrouter-laguna-s-2.1")

_lock = threading.Lock()
_broker: llmbroker.Broker | None = None
_exclusions_applied = False


def env_file() -> Path:
    return Path(settings.BASE_DIR) / ".env"


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
            _broker = llmbroker.Broker(
                settings.LLMBROKER_DATASOURCE,
                secrets=llmbroker.Secrets(env_file()),
                direct=direct_aliases(),
                home=settings.LLMBROKER_HOME,
            )
            atexit.register(_broker.close)
            _exclusions_applied = False
        if not _exclusions_applied:
            exclude_pool_llms(_broker)
            _exclusions_applied = True
        return _broker


def llms_for(user: Any) -> llmbroker.LLMs:
    return get_broker().for_scope(f"u-{user.id}")
