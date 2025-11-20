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
  - Skip OpenAI reasoning models (o*, gpt-5*, *reasoning*)
  - Skip OpenAI audio/gpt-audio, realtime, codex, instruct, legacy Davinci/Curie/Babbage/Ada,
    embeddings, moderation, etc.
  - Skip Anthropic reasoning models (*thinking*, *opus*)
  - Keep a blacklist of models that 404/500 so we don't keep retrying them
  - Record tokens, latency, per-1M-token prices and estimated cost per call
  - Print a per-prompt summary and save everything as llm_benchmark_YYYYMMDD_HHMMSS.json

Env:
  export OPENAI_API_KEY="sk-..."
  export ANTHROPIC_API_KEY="sk-ant-..."
"""

import os
import time
import json
import datetime as dt
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from collections import defaultdict

from openai import OpenAI
import anthropic


PROMPTS_DIR = Path("lexiflux/resources/prompts")

# Fixed test context you requested
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
    3. Append explicit language info at the bottom (just in case)
    """
    safe_vars = SafeFormatDict(
        text_language=TEXT_LANGUAGE,
        user_language=USER_LANGUAGE,
    )
    # Replace {text_language} / {user_language} if present
    formatted_template = template.format_map(safe_vars)

    # Mark the highlighted word
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
        f"target_language={USER_LANGUAGE}\n"  # explicit, even if template infers it
        f"word={HIGHLIGHT_WORD}\n"
    )

    full_input = formatted_template.strip() + "\n\n" + context_block
    return full_input


# ---------------------------------------------------------------------------
# 2) MODEL FILTERS
# ---------------------------------------------------------------------------


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


def is_openai_non_text_model(model_id: str, model_type: Optional[str]) -> bool:
    """
    Return True if this is not a text chat/responses model.

    - Filter by type when available (only keep 'chat.completions' / 'responses')
    - Additionally filter by name:
        * gpt-audio*, *realtime*, image, tts, whisper/transcribe/audio
        * embeddings, moderation
        * codex-*, code-*
        * instruct, davinci/curie/babbage/ada (old completions)
    """
    mid = model_id.lower()

    # First, type-based filter: only keep chat/responses
    if model_type not in (None, "chat.completions", "responses"):
        return True

    # Explicit name-based filters
    if mid.startswith("gpt-audio") or "audio-" in mid:
        return True
    if "realtime" in mid:
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

    # Moderation
    if "moderation" in mid or "omni-moderation" in mid:
        return True

    # Legacy code / codex
    if mid.startswith("codex-") or mid.startswith("code-"):
        return True

    # Instruct / legacy completions (tend to 404/500)
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
# 3) PRICING HELPERS (rough, but enough for comparison)
# ---------------------------------------------------------------------------


def openai_pricing_for_model(model_id: str) -> Tuple[Optional[float], Optional[float]]:
    mid = model_id.lower()

    # GPT-4.1 family
    if mid.startswith("gpt-4.1-mini"):
        return 0.40, 1.60
    if mid.startswith("gpt-4.1-nano"):
        return 0.10, 0.40
    if mid.startswith("gpt-4.1"):
        return 2.00, 8.00

    # GPT-4o mini
    if mid.startswith("gpt-4o-mini"):
        return 0.15, 0.60

    # GPT-4o
    if mid.startswith("gpt-4o"):
        return 2.50, 10.00

    # GPT-3.5 turbo (legacy but still useful as reference)
    if "gpt-3.5-turbo" in mid:
        return 0.50, 1.50

    # GPT-4 turbo / GPT-4 older
    if "gpt-4-turbo" in mid:
        return 10.00, 30.00
    if mid.startswith("gpt-4-32k"):
        return 60.00, 120.00
    if mid.startswith("gpt-4"):
        return 30.00, 60.00

    return None, None


def anthropic_pricing_for_model(model_id: str) -> Tuple[Optional[float], Optional[float]]:
    mid = model_id.lower()

    # Claude 3.7 / 3.5 Sonnet
    if "claude-3-7-sonnet" in mid or "claude-3.7-sonnet" in mid:
        return 3.00, 15.00
    if "claude-3-5-sonnet" in mid or "claude-3.5-sonnet" in mid:
        return 3.00, 15.00

    # Claude 3.5 Haiku
    if "claude-3-5-haiku" in mid or "claude-3.5-haiku" in mid:
        return 0.80, 4.00

    # Claude 3 Haiku
    if "claude-3-haiku" in mid and "3-5" not in mid and "3.5" not in mid:
        return 0.25, 1.25

    # Claude 3 Opus
    if "claude-3-opus" in mid:
        return 15.00, 75.00

    # Claude 4.x (rough guesses grouped with Sonnet/Haiku tiers)
    if "haiku-4.5" in mid:
        return 1.00, 5.00
    if "sonnet-4.5" in mid:
        return 3.00, 15.00
    if "sonnet-4" in mid and "4.5" not in mid:
        return 3.00, 15.00
    if "opus-4.1" in mid or "opus-4" in mid:
        return 15.00, 75.00

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
# 4) OPENAI: run models on prompts
# ---------------------------------------------------------------------------


def run_openai(raw_prompts: Dict[str, str]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set, skipping OpenAI.\n")
        return results

    client = OpenAI(api_key=api_key)

    model_objs = list(client.models.list())
    all_models = [(m.id, getattr(m, "type", None)) for m in model_objs]
    print(f"[OpenAI] Found {len(all_models)} models for this key.")

    filtered_model_ids: List[str] = []
    for mid, mtype in all_models:
        if is_openai_reasoning_model(mid):
            print(f"[OpenAI] Skipping reasoning model: {mid}")
            continue
        if is_openai_non_text_model(mid, mtype):
            print(f"[OpenAI] Skipping non-text/unsupported model: {mid} (type={mtype})")
            continue
        filtered_model_ids.append(mid)

    print(f"[OpenAI] Will run {len(filtered_model_ids)} text LLM models.\n")

    bad_models = set()

    for model_id in filtered_model_ids:
        if model_id in bad_models:
            continue

        for prompt_name, prompt_template in raw_prompts.items():
            if model_id in bad_models:
                break

            input_text = build_input_for_prompt(prompt_template)
            print(f"[OpenAI] Running model={model_id} on prompt={prompt_name} ...")
            start = time.perf_counter()
            try:
                response = client.responses.create(
                    model=model_id,
                    input=input_text,
                    max_output_tokens=512,
                    timeout=15,  # hard cap to avoid long hangs
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
                results.append(rec)

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
                results.append(rec)

                print(
                    f"[OpenAI] ✖ {model_id} | {prompt_name} | ERROR after {elapsed:.3f}s: {err_msg}"
                )

                # If it's clearly a model-not-found or 500, blacklist the model
                msg = str(e).lower()
                if "model" in msg and "not found" in msg:
                    bad_models.add(model_id)
                    print(f"[OpenAI] → Blacklisting {model_id} (model not found)")
                elif "500" in msg or "internalservererror" in msg:
                    bad_models.add(model_id)
                    print(f"[OpenAI] → Blacklisting {model_id} (internal error)")

    return results


# ---------------------------------------------------------------------------
# 5) ANTHROPIC: run non-reasoning models on prompts
# ---------------------------------------------------------------------------


def run_anthropic(raw_prompts: Dict[str, str]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set, skipping Anthropic.\n")
        return results

    client = anthropic.Anthropic(api_key=api_key)

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

    bad_models = set()

    for model_id in filtered_ids:
        if model_id in bad_models:
            continue

        for prompt_name, prompt_template in raw_prompts.items():
            if model_id in bad_models:
                break

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
                    timeout=15,
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
                results.append(rec)

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
                results.append(rec)

                print(
                    f"[Anthropic] ✖ {model_id} | {prompt_name} | "
                    f"ERROR after {elapsed:.3f}s: {err_msg}"
                )

                msg = str(e).lower()
                if "model" in msg and "not found" in msg:
                    bad_models.add(model_id)
                    print(f"[Anthropic] → Blacklisting {model_id} (model not found)")
                elif "500" in msg or "internal" in msg:
                    bad_models.add(model_id)
                    print(f"[Anthropic] → Blacklisting {model_id} (internal error)")

    return results


# ---------------------------------------------------------------------------
# 6) SUMMARY
# ---------------------------------------------------------------------------


def print_summary_grouped_by_prompt(all_results: List[Dict[str, Any]]) -> None:
    by_prompt: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in all_results:
        by_prompt[r["prompt_name"]].append(r)

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


# ---------------------------------------------------------------------------
# 7) MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    raw_prompts = load_raw_prompts_from_dir(PROMPTS_DIR)

    all_results: List[Dict[str, Any]] = []

    all_results.extend(run_openai(raw_prompts))
    all_results.extend(run_anthropic(raw_prompts))

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"llm_benchmark_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Saved {len(all_results)} records to {out_path}")

    print_summary_grouped_by_prompt(all_results)


if __name__ == "__main__":
    main()
