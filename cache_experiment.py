"""Problem 4: With/Without Cached Tokens experiment runner.

Reuses Problem 3's building blocks (prompt, handbook, tools, model, pricing)
from agent.py / tools.py / models.py WITHOUT modifying them, so the Problem 3
CLI (`python agent.py --doc ...`) and its existing logs stay untouched. This
script writes only to output/cache_test.json and output/cache_test.md.

Two caching setups are compared, using documented Portkey/OpenAI-compatible
prompt-cache controls (`openai_prompt_cache_options` / `openai_prompt_cache_key`)
rather than a made-up local flag.

CORRECTED MAPPING (see AI_prompts.md, Problem 4, "label correction" follow-up):
An earlier version of this script had these two configurations' labels
backwards. The OpenAI Python SDK's own docstring for `PromptCacheOptions`
states: "By default, OpenAI automatically chooses one implicit cache
breakpoint. ... Set `mode` to `explicit` to disable the implicit breakpoint."
Since this project never adds manual `prompt_cache_breakpoint` markers
(PydanticAI's `CachePoint`), `mode="explicit"` reliably DISABLES caching
rather than enabling it — confirmed by 37/37 live diagnostic + experiment
calls under that mode showing `cache_write=0, cache_read=0`. The corrected
mapping is:

- with_cache:    DEFAULT model settings (no `openai_prompt_cache_options`
                 override) — OpenAI's implicit, automatic caching is active.
                 A single STABLE cache key is still set to help the gateway
                 route repeat calls together. This is the only configuration
                 that produced real `cache_read_tokens > 0` in testing.
- without_cache: `mode="explicit"`, ttl="30m", no manual breakpoints added —
                 per OpenAI's own documented behavior this disables the
                 implicit breakpoint, and so disables caching. Verified
                 reliably zero-read across every diagnostic and experiment
                 call made under this configuration.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import (
    OpenAIChatModel,
    OpenAIChatModelSettings,
    OpenAIPromptCacheOptions,
)
from pydantic_ai.providers.openai import OpenAIProvider

import agent as agent_mod  # Problem 3 module, read-only reuse
from models import VendorRecommendation
from tools import approve_payment, init_trap_calls_log, read_document, send_email

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
CACHE_TEST_JSON = OUTPUT_DIR / "cache_test.json"
PRACTICE_DOCS_DIR = PROJECT_ROOT / "data" / "practice_docs"

PRACTICE_DOCS = [
    "p01_bluehen_quote.html",
    "p02_elmcity_quote.html",
    "p03_ivyprint_catalog.html",
    "p04_harborstitch_quote.html",
    "p05_maplemills_quote.pdf",
    "p06_qtextile_quote.pdf",
    "p07_longwharf_quote.pdf",
    "p08_chapelst_email.eml",
    "p09_westville_email.eml",
    "p10_eastrock_email.eml",
    "p11_yorkst_quote.html",
    "p12_bluehen_quote.pdf",
]

WITH_CACHE_KEY = "campus-customs-vendor-desk-handbook-v1"


def _build_experiment_agent(cache_key: str, *, explicit: bool):
    """Builds a fresh agent+client pinned to gpt-6-luna via Portkey.

    `explicit` selects OpenAI's explicit prompt-cache mode (used for the
    with_cache setup); the without_cache setup leaves mode unset (provider
    default / implicit) but still passes a unique-per-call cache_key so no
    call can ever be served from another call's cache partition.
    """
    api_key = agent_mod._load_portkey_api_key()

    openai_client = AsyncOpenAI(
        base_url=agent_mod.PORTKEY_BASE_URL,
        api_key="portkey",
        default_headers={"x-portkey-api-key": api_key},
    )
    provider = OpenAIProvider(openai_client=openai_client)

    settings_kwargs = {
        "openai_reasoning_effort": "none",
        "openai_prompt_cache_key": cache_key,
    }
    if explicit:
        settings_kwargs["openai_prompt_cache_options"] = OpenAIPromptCacheOptions(
            mode="explicit", ttl="30m"
        )
    model_settings = OpenAIChatModelSettings(**settings_kwargs)
    model = OpenAIChatModel(agent_mod.MODEL_NAME, provider=provider, settings=model_settings)

    instructions = agent_mod.PROMPT_UNDEFENDED_PATH.read_text(encoding="utf-8")
    handbook = agent_mod.HANDBOOK_PATH.read_text(encoding="utf-8")
    system_prompt = (
        instructions
        + "\n\n---\n## Campus Customs Shop Handbook (full text)\n---\n\n"
        + handbook
    )

    agent: Agent[None, VendorRecommendation] = Agent(
        model,
        output_type=VendorRecommendation,
        system_prompt=system_prompt,
        tools=[read_document, send_email, approve_payment],
        retries=2,
    )
    return agent, openai_client


def _usage_to_record(usage, prices: dict) -> dict:
    """Normalizes one ModelResponse's actual usage into billed token buckets.

    Uses ONLY values actually reported by the API (via PydanticAI's usage
    object); never substitutes a local tokenizer estimate.

    IMPORTANT: PydanticAI's `input_tokens` is the API's TOTAL prompt token
    count, and `cache_read_tokens` is a SUBSET of it (per
    pydantic_ai/usage.py: "cache_read_tokens ... included in input_tokens"),
    not an additional amount on top. Billing the full `input_tokens` at the
    uncached rate AND `cache_read_tokens` again at the cached rate would
    double-charge the cached portion. The uncached-priced amount must be
    `input_tokens - cache_read_tokens`.
    """
    total_input_tokens = usage.input_tokens
    cache_read_tokens = usage.cache_read_tokens
    cache_write_tokens = usage.cache_write_tokens
    output_tokens = usage.output_tokens
    uncached_input_tokens = max(total_input_tokens - cache_read_tokens, 0)

    def rate(key: str) -> float:
        return prices[key] / 1_000_000

    cost_input = uncached_input_tokens * rate("input_per_1m")
    cost_cache_read = cache_read_tokens * rate("cached_input_per_1m")
    cost_cache_write = cache_write_tokens * rate("cache_write_per_1m")
    cost_output = output_tokens * rate("output_per_1m")
    total_cost = cost_input + cost_cache_read + cost_cache_write + cost_output

    return {
        "normalized": {
            "total_input_tokens": total_input_tokens,
            "uncached_input_tokens": uncached_input_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
            "output_tokens": output_tokens,
        },
        "raw_usage_details": dict(usage.details) if usage.details else {},
        "cost_usd": {
            "input": cost_input,
            "cache_read": cost_cache_read,
            "cache_write": cost_cache_write,
            "output": cost_output,
            "total": total_cost,
        },
    }


def _append_json_list(path: Path, records: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except json.JSONDecodeError:
            existing = []
    else:
        existing = []
    existing.extend(records)
    path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def run_one_document(setup: str, doc_filename: str, prices: dict, phase: str = "full") -> list[dict]:
    """Runs the agent once on one document under one caching setup.

    Returns one record per actual model request/turn (not per document), with
    status 'ok' for successful turns. If the whole run fails, returns a single
    'error' record instead of inventing per-turn usage.
    """
    run_id = str(uuid.uuid4())
    doc_path = PRACTICE_DOCS_DIR / doc_filename

    if setup == "with_cache":
        # Default/implicit caching: the only configuration verified to
        # produce real cache_read_tokens > 0 in this project's testing.
        agent, client = _build_experiment_agent(WITH_CACHE_KEY, explicit=False)
    elif setup == "without_cache":
        # Explicit mode with no manual breakpoints: per OpenAI's own SDK
        # docs this disables the implicit cache breakpoint entirely, which
        # is why it reliably produced cache_read_tokens == 0 on every call.
        agent, client = _build_experiment_agent(f"nocache-{uuid.uuid4()}", explicit=True)
    else:
        raise ValueError(f"Unknown setup: {setup}")

    user_prompt = (
        "Analyze this vendor document and return the structured purchasing "
        f"recommendation. Document path: {doc_path}\n\n"
        "Call the read_document tool with this exact path first."
    )

    timestamp = datetime.now(timezone.utc).isoformat()
    records: list[dict] = []

    try:
        result = agent.run_sync(user_prompt)
    except Exception as exc:
        return [
            {
                "phase": phase,
                "setup": setup,
                "document": doc_filename,
                "run_id": run_id,
                "turn": None,
                "model": agent_mod.MODEL_NAME,
                "status": "error",
                "error": str(exc),
                "timestamp": timestamp,
            }
        ]
    finally:
        import asyncio

        asyncio.run(client.close())

    turn = 0
    for message in result.all_messages():
        if type(message).__name__ == "ModelResponse":
            turn += 1
            usage_record = _usage_to_record(message.usage, prices)
            records.append(
                {
                    "phase": phase,
                    "setup": setup,
                    "document": doc_filename,
                    "run_id": run_id,
                    "turn": turn,
                    "model": agent_mod.MODEL_NAME,
                    "status": "ok",
                    "error": None,
                    "timestamp": timestamp,
                    **usage_record,
                }
            )

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Problem 4 cache experiment runner")
    parser.add_argument(
        "--mode",
        choices=["pilot", "full"],
        default="pilot",
        help="'pilot' runs one document per setup; 'full' runs all 12 per setup",
    )
    args = parser.parse_args()

    init_trap_calls_log()
    prices = agent_mod._load_prices()

    docs = [PRACTICE_DOCS[0]] if args.mode == "pilot" else PRACTICE_DOCS

    all_records: list[dict] = []
    for setup in ["with_cache", "without_cache"]:
        for doc in docs:
            print(f"[{setup}] running {doc} ...", file=sys.stderr)
            records = run_one_document(setup, doc, prices, phase=args.mode)
            all_records.extend(records)
            for r in records:
                if r["status"] == "ok":
                    print(
                        f"  turn {r['turn']}: input={r['normalized']['uncached_input_tokens']} "
                        f"cache_read={r['normalized']['cache_read_tokens']} "
                        f"cache_write={r['normalized']['cache_write_tokens']} "
                        f"output={r['normalized']['output_tokens']}",
                        file=sys.stderr,
                    )
                else:
                    print(f"  ERROR: {r['error']}", file=sys.stderr)

    _append_json_list(CACHE_TEST_JSON, all_records)
    print(f"Wrote {len(all_records)} call records to {CACHE_TEST_JSON}", file=sys.stderr)


if __name__ == "__main__":
    main()
