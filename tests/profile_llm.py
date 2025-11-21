#!/usr/bin/env python3
"""
bench_llms.py

Benchmark all suitable *text* LLM models from OpenAI and Anthropic
on ALL prompt-templates in lexiflux/resources/prompts/*.txt.

For each prompt we:
  - load its template from a .txt file
  - combine it with a fixed test context:
      text_language = "Serbian"
      user_language = "Russian"
      fragment = 'video kraj sebe mračnog bradatog komarca koji se trudio da zarije '
                 'svoje debelo, kao hemijska olovka, rilo meni u list.'
      highlighted word = 'list' (wrapped in [HIGHLIGHT]...[/HIGHLIGHT])

We:
  - Skip OpenAI:
      * reasoning models (o*, gpt-5*, *reasoning*)
      * audio / gpt-audio*, Sora, realtime (*realtime*), image models,
      * TTS / STT models (tts, whisper, transcribe, audio-),
      * embeddings, moderation,
      * codex-*, code-*,
      * instruct, old GPT-3 completions (davinci/curie/babbage/ada).
  - Skip Anthropic reasoning models (*thinking*, *opus*).
  - Keep a blacklist of models that 404/500 so we don't keep retrying them.
  - Record tokens, latency, per-1M-token prices and estimated cost per call.
  - Update the JSON file after *every* result (success or error).
  - With --resume, read the existing JSON, skip already completed (provider, model, prompt)
    and reuse known bad-model blacklists.
  - At the end, print:
      * per-prompt summary
      * total cost (overall and per provider).

Usage examples:

  python bench_llms.py
  python bench_llms.py --output my_run.json
  python bench_llms.py --resume --output my_run.json

Env:
  export OPENAI_API_KEY="sk-..."
  export ANTHROPIC_API_KEY="sk-ant-..."
"""

import os
import time
import json
import argparse
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from collections import defaultdict

from openai import OpenAI
import anthropic


PROMPTS_DIR = Path("lexiflux/resources/prompts")
BLACKLIST_PATH = Path(__file__).parent / "llm_blacklist.json"
PRICES_PATH = Path(__file__).parent / "llm_prices.json"

# Fixed test context
TEXT_LANGUAGE = "Serbian"
USER_LANGUAGE = "Russian"
TEXT_FRAGMENT = (
    "video kraj sebe mračnog bradatog komarca koji se trudio da zarije "
    "svoje debelo, kao hemijska olovka, rilo meni u list."
)
HIGHLIGHT_WORD = "list"


# ---------------------------------------------------------------------------
# 1) PROMPT LOADING + CONTEXT INJECTION
# ---------------------------------------------------------------------------


class SafeFormatDict(dict):
    """For .format_map: leave unknown {placeholders} untouched."""

    def __missing__(self, key):
        return "{" + key + "}"


def load_raw_prompts_from_dir(directory: Path) -> Dict[str, str]:
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Prompt directory not found: {directory.resolve()}")

    prompts: Dict[str, str] = {}
    for path in sorted(directory.glob("*.txt")):
        if not path.is_file():
            continue
        name = path.stem
        text = path.read_text(encoding="utf-8")
        prompts[name] = text

    if not prompts:
        raise RuntimeError(f"No .txt prompts found in {directory.resolve()}")

    print(f"Loaded {len(prompts)} prompt templates from {directory.resolve()}:")
    for name in prompts:
        print(f"  - {name}")
    print()
    return prompts


def build_input_for_prompt(template: str) -> str:
    """
    Combine a single prompt template with your fixed test context.

    1. Format known placeholders: {text_language}, {user_language}
    2. Inject [FRAGMENT]...[/FRAGMENT] with [HIGHLIGHT]list[/HIGHLIGHT]
    3. Append explicit language + word info at the bottom
    """
    safe_vars = SafeFormatDict(
        text_language=TEXT_LANGUAGE,
        user_language=USER_LANGUAGE,
    )
    # Replace {text_language} / {user_language} if present
    formatted_template = template.format_map(safe_vars)

    # Mark the highlighted word once
    marked_fragment = TEXT_FRAGMENT.replace(
        HIGHLIGHT_WORD,
        f"[HIGHLIGHT]{HIGHLIGHT_WORD}[/HIGHLIGHT]",
        1,
    )

    context_block = (
        "[FRAGMENT]\n"
        f"{marked_fragment}\n"
        "[/FRAGMENT]\n\n"
        f"text_language={TEXT_LANGUAGE}\n"
        f"user_language={USER_LANGUAGE}\n"
        f"target_language={USER_LANGUAGE}\n"
        f"word={HIGHLIGHT_WORD}\n"
    )

    full_input = formatted_template.strip() + "\n\n" + context_block
    return full_input


# ---------------------------------------------------------------------------
# 2) MODEL FILTERS + BLACKLIST
# ---------------------------------------------------------------------------


def load_blacklist() -> set:
    """Load blacklist from JSON file."""
    if not BLACKLIST_PATH.exists():
        print(f"[WARN] Blacklist file not found: {BLACKLIST_PATH}, using empty blacklist.")
        return set()
    try:
        with BLACKLIST_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            models = data.get("models", [])
            return set(models)
    except Exception as e:
        print(f"[WARN] Could not load blacklist from {BLACKLIST_PATH}: {e}, using empty blacklist.")
        return set()


_BLACKLIST_CACHE: Optional[set] = None


def get_blacklist() -> set:
    """Get blacklist (cached)."""
    global _BLACKLIST_CACHE
    if _BLACKLIST_CACHE is None:
        _BLACKLIST_CACHE = load_blacklist()
    return _BLACKLIST_CACHE


def is_blacklisted(provider: str, model_id: str) -> bool:
    """Check if a model is blacklisted."""
    blacklist = get_blacklist()
    key = f"{provider}:{model_id}"
    return key in blacklist


def is_openai_reasoning_model(model_id: str) -> bool:
    mid = model_id.lower()
    if mid.startswith("o1-"):
        return True
    if mid.startswith("o3-"):
        return True
    if mid.startswith("o4-"):
        return True
    if mid.startswith("gpt-5"):
        return True
    if "reasoning" in mid:
        return True
    return False


def is_openai_non_text_model(model_id: str) -> bool:
    """
    Return True if this is NOT a text chat/responses model we want to call.

    We filter by name because OpenAI's models.list() returns models for many
    endpoints (audio, images, embeddings, moderation, realtime, Sora, etc.),
    and some legacy completions that 404/500 on modern endpoints.
    """
    mid = model_id.lower()

    # Sora (video)
    if "sora" in mid:
        return True

    # Realtime
    if "realtime" in mid:
        return True

    # Audio / gpt-audio
    if mid.startswith("gpt-audio") or "audio-" in mid:
        return True

    # Images
    if "dall-e" in mid or "gpt-image" in mid or "image-" in mid:
        return True

    # TTS / STT
    if mid.startswith("tts-") or "tts" in mid:
        return True
    if "whisper" in mid or "transcribe" in mid:
        return True

    # Embeddings
    if "embedding" in mid:
        return True

    # Moderation / safety-only
    if "moderation" in mid or "omni-moderation" in mid:
        return True

    # Legacy code / codex
    if mid.startswith("codex-") or mid.startswith("code-"):
        return True

    # Instruct / legacy completions
    if "instruct" in mid:
        return True

    # Old GPT-3 era completions
    if any(x in mid for x in ("davinci", "curie", "babbage", "ada")):
        return True

    return False


def is_anthropic_reasoning_model(model_id: str) -> bool:
    mid = model_id.lower()
    if "thinking" in mid:
        return True
    if "opus" in mid:
        return True
    return False


# ---------------------------------------------------------------------------
# 3) PRICING HELPERS (read from JSON file)
# ---------------------------------------------------------------------------


def load_prices() -> Dict[str, Dict[str, Dict[str, float]]]:
    """Load pricing data from JSON file."""
    if not PRICES_PATH.exists():
        print(f"[WARN] Prices file not found: {PRICES_PATH}, using empty prices.")
        return {}
    try:
        with PRICES_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Could not load prices from {PRICES_PATH}: {e}, using empty prices.")
        return {}


_PRICES_CACHE: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None


def get_prices() -> Dict[str, Dict[str, Dict[str, float]]]:
    """Get prices (cached)."""
    global _PRICES_CACHE
    if _PRICES_CACHE is None:
        _PRICES_CACHE = load_prices()
    return _PRICES_CACHE


def openai_pricing_for_model(model_id: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Return (input_price_per_1M_tokens, output_price_per_1M_tokens) in USD
    for known OpenAI *text* chat models.

    If unknown, returns (None, None).
    """
    prices = get_prices()
    openai_prices = prices.get("openai", {})

    mid = model_id.lower()

    # Try exact match first
    for key, price_info in openai_prices.items():
        if key.lower() == mid:
            return price_info.get("input_price_per_mtoken"), price_info.get(
                "output_price_per_mtoken"
            )

    # Try prefix matches (for versioned models)
    for key, price_info in openai_prices.items():
        key_lower = key.lower()
        if mid.startswith(key_lower) or key_lower in mid:
            return price_info.get("input_price_per_mtoken"), price_info.get(
                "output_price_per_mtoken"
            )

    return None, None


def anthropic_pricing_for_model(model_id: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Return (input_price_per_1M_tokens, output_price_per_1M_tokens) in USD
    for known Claude models. Values from Anthropic pricing table.
    """
    prices = get_prices()
    anthropic_prices = prices.get("anthropic", {})

    mid = model_id.lower()

    # Try exact match first
    for key, price_info in anthropic_prices.items():
        if key.lower() == mid:
            return price_info.get("input_price_per_mtoken"), price_info.get(
                "output_price_per_mtoken"
            )

    # Try substring matches (for versioned models)
    for key, price_info in anthropic_prices.items():
        key_lower = key.lower()
        if key_lower in mid or mid in key_lower:
            return price_info.get("input_price_per_mtoken"), price_info.get(
                "output_price_per_mtoken"
            )

    return None, None


def estimate_cost_usd(
    input_tokens: int,
    output_tokens: int,
    input_price_per_m: Optional[float],
    output_price_per_m: Optional[float],
) -> Optional[float]:
    if input_price_per_m is None or output_price_per_m is None:
        return None
    return (input_tokens / 1_000_000.0) * input_price_per_m + (
        output_tokens / 1_000_000.0
    ) * output_price_per_m


# ---------------------------------------------------------------------------
# 4) JSON WRITER (incremental updates)
# ---------------------------------------------------------------------------


def write_results(output_path: Path, results: List[Dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 5) OPENAI: run models on prompts (with resume + blacklist)
# ---------------------------------------------------------------------------


def run_openai(
    raw_prompts: Dict[str, str],
    output_path: Path,
    all_results: List[Dict[str, Any]],
    completed_keys: set,
    bad_models: set,
) -> Tuple[List[Dict[str, Any]], set]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set, skipping OpenAI.\n")
        return all_results, bad_models

    # Shorter timeout + fewer retries so bad models don't hang forever.
    client = OpenAI(api_key=api_key, timeout=20.0, max_retries=1)

    model_objs = list(client.models.list())
    model_ids = [m.id for m in model_objs]
    print(f"[OpenAI] Found {len(model_ids)} models for this key.")

    filtered_model_ids: List[str] = []
    for mid in model_ids:
        if is_openai_reasoning_model(mid):
            print(f"[OpenAI] Skipping reasoning model: {mid}")
            continue
        if is_openai_non_text_model(mid):
            print(f"[OpenAI] Skipping non-text/unsupported model: {mid}")
            continue
        filtered_model_ids.append(mid)

    print(f"[OpenAI] Will run {len(filtered_model_ids)} text LLM models.\n")

    for model_id in filtered_model_ids:
        if model_id in bad_models:
            print(f"[OpenAI] Skipping blacklisted model: {model_id}")
            continue
        if is_blacklisted("openai", model_id):
            print(f"[OpenAI] Skipping blacklisted model (from JSON): {model_id}")
            continue

        for prompt_name, prompt_template in raw_prompts.items():
            if model_id in bad_models:
                break

            key = ("openai", model_id, prompt_name)
            if key in completed_keys:
                # Already done in a previous run (resume mode)
                continue

            input_text = build_input_for_prompt(prompt_template)
            print(f"[OpenAI] Running model={model_id} on prompt={prompt_name} ...")
            start = time.perf_counter()
            try:
                # Per-request override for timeout, just in case
                response = client.with_options(timeout=20.0).responses.create(
                    model=model_id,
                    input=input_text,
                    max_output_tokens=512,
                )
                elapsed = time.perf_counter() - start

                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
                output_tokens = getattr(usage, "output_tokens", 0) if usage else 0

                in_price_m, out_price_m = openai_pricing_for_model(model_id)
                est_cost = estimate_cost_usd(input_tokens, output_tokens, in_price_m, out_price_m)

                output_text = getattr(response, "output_text", None)

                rec = {
                    "provider": "openai",
                    "model": model_id,
                    "prompt_name": prompt_name,
                    "elapsed_sec": elapsed,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "input_price_per_mtoken": in_price_m,
                    "output_price_per_mtoken": out_price_m,
                    "estimated_cost_usd": est_cost,
                    "output": output_text,
                    "error": None,
                }
                all_results.append(rec)
                completed_keys.add(key)
                write_results(output_path, all_results)

                print(
                    f"[OpenAI] ✔ {model_id} | {prompt_name} | "
                    f"{elapsed:.3f}s | tokens in={input_tokens} out={output_tokens} | "
                    f"cost={est_cost if est_cost is not None else 'unknown'}"
                )
            except Exception as e:
                elapsed = time.perf_counter() - start
                err_msg = f"{type(e).__name__}: {e}"

                rec = {
                    "provider": "openai",
                    "model": model_id,
                    "prompt_name": prompt_name,
                    "elapsed_sec": elapsed,
                    "input_tokens": None,
                    "output_tokens": None,
                    "input_price_per_mtoken": None,
                    "output_price_per_mtoken": None,
                    "estimated_cost_usd": None,
                    "output": None,
                    "error": err_msg,
                }
                all_results.append(rec)
                completed_keys.add(key)
                write_results(output_path, all_results)

                print(
                    f"[OpenAI] ✖ {model_id} | {prompt_name} | ERROR after {elapsed:.3f}s: {err_msg}"
                )

                # Heuristics: if it's clearly model-not-found or internal error,
                # blacklist the model so we don't keep hitting it.
                msg = str(e).lower()
                if ("model" in msg and "not found" in msg) or "was not found" in msg:
                    bad_models.add(model_id)
                    print(f"[OpenAI] → Blacklisting {model_id} (model not found)")
                elif (
                    "error code: 500" in msg
                    or "internalservererror" in msg
                    or "internal server error" in msg
                    or "status_code: 500" in msg
                ):
                    bad_models.add(model_id)
                    print(f"[OpenAI] → Blacklisting {model_id} (internal error)")

    return all_results, bad_models


# ---------------------------------------------------------------------------
# 6) ANTHROPIC: run non-reasoning models on prompts (with resume + blacklist)
# ---------------------------------------------------------------------------


def run_anthropic(
    raw_prompts: Dict[str, str],
    output_path: Path,
    all_results: List[Dict[str, Any]],
    completed_keys: set,
    bad_models: set,
) -> Tuple[List[Dict[str, Any]], set]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set, skipping Anthropic.\n")
        return all_results, bad_models

    # Set a reasonable timeout + limited retries
    client = anthropic.Anthropic(api_key=api_key, timeout=20.0, max_retries=1)

    models_list = client.models.list()
    all_ids = [m.id for m in models_list.data]
    print(f"[Anthropic] Found {len(all_ids)} models for this key.")

    filtered_ids = []
    for mid in all_ids:
        if is_anthropic_reasoning_model(mid):
            print(f"[Anthropic] Skipping reasoning model: {mid}")
            continue
        filtered_ids.append(mid)

    print(f"[Anthropic] Will run {len(filtered_ids)} non-reasoning models.\n")

    for model_id in filtered_ids:
        if model_id in bad_models:
            print(f"[Anthropic] Skipping blacklisted model: {model_id}")
            continue
        if is_blacklisted("anthropic", model_id):
            print(f"[Anthropic] Skipping blacklisted model (from JSON): {model_id}")
            continue

        for prompt_name, prompt_template in raw_prompts.items():
            if model_id in bad_models:
                break

            key = ("anthropic", model_id, prompt_name)
            if key in completed_keys:
                continue

            input_text = build_input_for_prompt(prompt_template)
            print(f"[Anthropic] Running model={model_id} on prompt={prompt_name} ...")
            start = time.perf_counter()
            try:
                message = client.messages.create(
                    model=model_id,
                    max_tokens=512,
                    messages=[
                        {"role": "user", "content": input_text},
                    ],
                )
                elapsed = time.perf_counter() - start

                usage = getattr(message, "usage", None)
                input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
                output_tokens = getattr(usage, "output_tokens", 0) if usage else 0

                in_price_m, out_price_m = anthropic_pricing_for_model(model_id)
                est_cost = estimate_cost_usd(input_tokens, output_tokens, in_price_m, out_price_m)

                parts: List[str] = []
                for block in message.content:
                    if hasattr(block, "type") and block.type == "text":
                        parts.append(getattr(block, "text", "") or "")
                    elif isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", "") or "")
                output_text = "".join(parts)

                rec = {
                    "provider": "anthropic",
                    "model": model_id,
                    "prompt_name": prompt_name,
                    "elapsed_sec": elapsed,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "input_price_per_mtoken": in_price_m,
                    "output_price_per_mtoken": out_price_m,
                    "estimated_cost_usd": est_cost,
                    "output": output_text,
                    "error": None,
                }
                all_results.append(rec)
                completed_keys.add(key)
                write_results(output_path, all_results)

                print(
                    f"[Anthropic] ✔ {model_id} | {prompt_name} | "
                    f"{elapsed:.3f}s | tokens in={input_tokens} out={output_tokens} | "
                    f"cost={est_cost if est_cost is not None else 'unknown'}"
                )
            except Exception as e:
                elapsed = time.perf_counter() - start
                err_msg = f"{type(e).__name__}: {e}"

                rec = {
                    "provider": "anthropic",
                    "model": model_id,
                    "prompt_name": prompt_name,
                    "elapsed_sec": elapsed,
                    "input_tokens": None,
                    "output_tokens": None,
                    "input_price_per_mtoken": None,
                    "output_price_per_mtoken": None,
                    "estimated_cost_usd": None,
                    "output": None,
                    "error": err_msg,
                }
                all_results.append(rec)
                completed_keys.add(key)
                write_results(output_path, all_results)

                print(
                    f"[Anthropic] ✖ {model_id} | {prompt_name} | "
                    f"ERROR after {elapsed:.3f}s: {err_msg}"
                )

                msg = str(e).lower()
                if ("model" in msg and "not found" in msg) or "was not found" in msg:
                    bad_models.add(model_id)
                    print(f"[Anthropic] → Blacklisting {model_id} (model not found)")
                elif (
                    "error code: 500" in msg
                    or "internal" in msg  # catch InternalServerError variants
                ):
                    bad_models.add(model_id)
                    print(f"[Anthropic] → Blacklisting {model_id} (internal error)")

    return all_results, bad_models


# ---------------------------------------------------------------------------
# 7) SUMMARY (per prompt + total cost)
# ---------------------------------------------------------------------------


def print_summary_grouped_by_prompt(all_results: List[Dict[str, Any]]) -> None:
    by_prompt: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    total_cost = 0.0
    by_provider_cost: Dict[str, float] = defaultdict(float)

    for r in all_results:
        by_prompt[r["prompt_name"]].append(r)
        c = r.get("estimated_cost_usd")
        if c is not None:
            total_cost += c
            by_provider_cost[r["provider"]] += c

    print("\n================ SUMMARY BY PROMPT ================\n")
    for prompt_name, items in by_prompt.items():
        print(f"=== Prompt: {prompt_name} ===")

        # sort by cost (unknown last), then by elapsed
        def sort_key(rec: Dict[str, Any]):
            cost = rec.get("estimated_cost_usd")
            cost_key = cost if (cost is not None) else 1e9
            return (cost_key, rec.get("elapsed_sec") or 0.0)

        for rec in sorted(items, key=sort_key):
            provider = rec["provider"]
            model = rec["model"]
            elapsed = rec["elapsed_sec"]
            in_tok = rec.get("input_tokens")
            out_tok = rec.get("output_tokens")
            cost = rec.get("estimated_cost_usd")
            error = rec.get("error")
            cost_str = f"${cost:.8f}" if cost is not None else "unknown"
            print(
                f" - [{provider}] {model} | "
                f"{elapsed:.3f}s | tokens in={in_tok} out={out_tok} | "
                f"cost={cost_str} | error={error}"
            )
        print()

    print("=============== COST SUMMARY =================")
    print(f"Total cost (all providers): ${total_cost:.8f}")
    for provider, c in by_provider_cost.items():
        print(f"  - {provider}: ${c:.8f}")
    print("===============================================")


# ---------------------------------------------------------------------------
# 8) ARG PARSING + RESUME LOGIC
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bench all OpenAI + Anthropic text models on LexiFlux prompts."
    )
    parser.add_argument(
        "--output",
        "-o",
        default="llm_benchmark.json",
        help="Path to JSON file with results (default: llm_benchmark.json)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing JSON file: skip already completed "
        "(provider, model, prompt) and reuse bad-model blacklist.",
    )
    return parser.parse_args()


def load_existing_results_for_resume(
    output_path: Path,
) -> Tuple[List[Dict[str, Any]], set, set, set]:
    """
    Load existing JSON (if any) and reconstruct:

    - all_results: the list itself
    - completed_keys: set of (provider, model, prompt_name)
    - openai_bad_models: models we should skip immediately
    - anthropic_bad_models: models we should skip immediately
    """
    all_results: List[Dict[str, Any]] = []
    completed_keys: set = set()
    openai_bad_models: set = set()
    anthropic_bad_models: set = set()

    if not output_path.exists():
        return all_results, completed_keys, openai_bad_models, anthropic_bad_models

    try:
        with output_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"[WARN] Existing file {output_path} is not a list; ignoring for resume.")
            return all_results, completed_keys, openai_bad_models, anthropic_bad_models
        all_results = data
    except Exception as e:
        print(f"[WARN] Could not parse existing JSON {output_path}: {e}")
        return all_results, completed_keys, openai_bad_models, anthropic_bad_models

    for r in all_results:
        provider = r.get("provider")
        model = r.get("model")
        prompt_name = r.get("prompt_name")
        if not provider or not model or not prompt_name:
            continue
        completed_keys.add((provider, model, prompt_name))

        err = (r.get("error") or "").lower()
        if not err:
            continue

        # Rebuild bad-model blacklist from previous runs
        if provider == "openai":
            if ("model" in err and "not found" in err) or "was not found" in err:
                openai_bad_models.add(model)
            elif (
                "error code: 500" in err
                or "internalservererror" in err
                or "internal server error" in err
                or "status_code: 500" in err
            ):
                openai_bad_models.add(model)
        elif provider == "anthropic":
            if ("model" in err and "not found" in err) or "was not found" in err:
                anthropic_bad_models.add(model)
            elif "error code: 500" in err or "internal" in err:
                anthropic_bad_models.add(model)

    print(
        f"[RESUME] Loaded {len(all_results)} existing records from {output_path}. "
        f"Completed combos: {len(completed_keys)}, "
        f"OpenAI bad models: {len(openai_bad_models)}, "
        f"Anthropic bad models: {len(anthropic_bad_models)}"
    )
    return all_results, completed_keys, openai_bad_models, anthropic_bad_models


# ---------------------------------------------------------------------------
# 9) MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)

    raw_prompts = load_raw_prompts_from_dir(PROMPTS_DIR)

    if args.resume:
        all_results, completed_keys, openai_bad_models, anthropic_bad_models = (
            load_existing_results_for_resume(output_path)
        )
    else:
        all_results = []
        completed_keys = set()
        openai_bad_models = set()
        anthropic_bad_models = set()

    # Run OpenAI + Anthropic. Each call will update all_results and JSON incrementally.
    all_results, openai_bad_models = run_openai(
        raw_prompts,
        output_path,
        all_results,
        completed_keys,
        openai_bad_models,
    )
    all_results, anthropic_bad_models = run_anthropic(
        raw_prompts,
        output_path,
        all_results,
        completed_keys,
        anthropic_bad_models,
    )

    # Final write (just in case)
    write_results(output_path, all_results)
    print(f"\nDone. Total records stored in {output_path}: {len(all_results)}")

    # Human-readable summary you asked for:
    print_summary_grouped_by_prompt(all_results)


if __name__ == "__main__":
    main()
