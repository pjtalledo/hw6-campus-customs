"""Accounting-only correction of the historical cached-token double-counting
bug in output/usage_log.json, for Problem 5/6/7 entries ONLY (indices 2-37).

Does NOT touch: raw token counts (input_tokens, cache_read_tokens,
cache_write_tokens, output_tokens), timestamps, documents, model, defense_mode,
or any model-generated content anywhere. Only the derived `cost_usd` sub-object
is recomputed from the existing raw token counts using the corrected formula
(same one already used in cache_experiment.py since Problem 4, and in
agent.py since Problem 8): cache_read_tokens is a SUBSET of input_tokens, so
only (input_tokens - cache_read_tokens) is billed at the uncached rate.

Rounding policy: each cost component rounded to 8 decimal places, matching
agent.py's existing convention, for consistency with Problem 3/8's figures.

Problem 3's original 2 entries (indices 0-1, both cache_read_tokens == 0,
mathematically unaffected by the bug) and Problem 8's exam entries
(indices 38-47, already computed with the fixed formula) are left untouched.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
USAGE_LOG_PATH = ROOT / "output" / "usage_log.json"
PRICES = json.loads((ROOT / "data" / "prices.json").read_text(encoding="utf-8"))["gpt-6-luna"]

AFFECTED_RANGE = (2, 38)  # Python slice [2:38] = indices 2..37 inclusive = Problems 5,6,7


def rate(key: str) -> float:
    return PRICES[key] / 1_000_000


def corrected_cost(entry: dict) -> dict:
    input_tokens = entry["input_tokens"]
    cache_read_tokens = entry["cache_read_tokens"]
    cache_write_tokens = entry["cache_write_tokens"]
    output_tokens = entry["output_tokens"]

    uncached_input_tokens = max(input_tokens - cache_read_tokens, 0)

    cost_input = uncached_input_tokens * rate("input_per_1m")
    cost_cache_read = cache_read_tokens * rate("cached_input_per_1m")
    cost_cache_write = cache_write_tokens * rate("cache_write_per_1m")
    cost_output = output_tokens * rate("output_per_1m")
    total_cost = cost_input + cost_cache_read + cost_cache_write + cost_output

    return {
        "input": round(cost_input, 8),
        "cache_read": round(cost_cache_read, 8),
        "cache_write": round(cost_cache_write, 8),
        "output": round(cost_output, 8),
        "total": round(total_cost, 8),
    }


def main() -> None:
    usage = json.loads(USAGE_LOG_PATH.read_text(encoding="utf-8"))
    assert len(usage) == 48, f"Expected 48 usage_log entries, found {len(usage)} -- aborting to avoid touching the wrong rows."

    corrections = []
    for i in range(*AFFECTED_RANGE):
        entry = usage[i]
        old_cost = entry["cost_usd"]
        new_cost = corrected_cost(entry)
        corrections.append(
            {
                "index": i,
                "document": entry.get("document"),
                "defense_mode": entry.get("defense_mode"),
                "input_tokens": entry["input_tokens"],
                "cache_read_tokens": entry["cache_read_tokens"],
                "cache_write_tokens": entry["cache_write_tokens"],
                "output_tokens": entry["output_tokens"],
                "old_cost_total": old_cost["total"],
                "new_cost_total": new_cost["total"],
                "overstatement": round(old_cost["total"] - new_cost["total"], 8),
            }
        )
        entry["cost_usd"] = new_cost
        entry["cost_correction_note"] = (
            "cost_usd corrected retrospectively for the cached-token "
            "double-counting bug (see output/cost_correction_audit.md); "
            "raw token counts above are unchanged from the original API response."
        )

    USAGE_LOG_PATH.write_text(json.dumps(usage, indent=2, ensure_ascii=False), encoding="utf-8")

    Path(ROOT / "output" / "cost_correction_raw_deltas.json").write_text(
        json.dumps(corrections, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    old_total = sum(c["old_cost_total"] for c in corrections)
    new_total = sum(c["new_cost_total"] for c in corrections)
    print(f"Corrected {len(corrections)} usage_log.json entries (indices {AFFECTED_RANGE[0]}-{AFFECTED_RANGE[1]-1}).")
    print(f"Old (buggy) total: {old_total:.8f}")
    print(f"New (corrected) total: {new_total:.8f}")
    print(f"Overstatement removed: {old_total - new_total:.8f}")


if __name__ == "__main__":
    main()
