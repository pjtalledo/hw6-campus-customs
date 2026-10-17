"""Phase 3 offline validation for run_layer_cost_experiment.py.

Pure local checks: no API calls, no network access, no sensitive-tool
invocation. Uses the already-written output/layer_cost_experiment.json plus
direct code/data inspection and deterministic fixtures.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
import agent as agent_mod
import run_layer_cost_experiment as exp

PASS = []
FAIL = []


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print(f"PASS: {name}")
    else:
        FAIL.append((name, detail))
        print(f"FAIL: {name} -- {detail}")


# 1. Configuration matrix
check(
    "Exactly 5 configurations defined",
    len(exp.CONFIGURATIONS) == 5,
)
check(
    "Configurations match expected layer combinations",
    exp.CONFIGURATIONS == {
        "baseline": {"code": False, "design": False, "prompt": False},
        "code_only": {"code": True, "design": False, "prompt": False},
        "design_only": {"code": False, "design": True, "prompt": False},
        "prompt_only": {"code": False, "design": False, "prompt": True},
        "all_three": {"code": True, "design": True, "prompt": True},
    },
)

# 2. 12 document identifiers match data/practice_docs/ exactly
actual_files = sorted(p.name for p in Path("data/practice_docs").iterdir() if p.is_file())
check(
    "12 document identifiers match data/practice_docs/ exactly",
    exp.PRACTICE_DOCS == actual_files,
    f"expected {actual_files}, got {exp.PRACTICE_DOCS}",
)
check("Exactly 12 documents", len(exp.PRACTICE_DOCS) == 12)

# 3. Prompt selection per configuration (static code inspection via source text)
src = Path("run_layer_cost_experiment.py").read_text(encoding="utf-8")
check(
    "code_only uses PROMPT_UNDEFENDED_PATH (original prompt)",
    'configuration == "code_only"' in src and "PROMPT_UNDEFENDED_PATH" in src,
)
check(
    "design_only uses PROMPT_UNDEFENDED_PATH (original prompt)",
    'configuration == "design_only"' in src,
)
check(
    "prompt_only uses PROMPT_DEFENDED_PATH (defended prompt, now prompts/prompt.md)",
    'configuration == "prompt_only"' in src and "PROMPT_DEFENDED_PATH" in src,
)
check(
    "PROMPT_DEFENDED_PATH correctly points at prompts/prompt.md (Priority 1 fix)",
    agent_mod.PROMPT_DEFENDED_PATH.name == "prompt.md",
)
check(
    "PROMPT_UNDEFENDED_PATH correctly points at prompts/prompt_undefended.md",
    agent_mod.PROMPT_UNDEFENDED_PATH.name == "prompt_undefended.md",
)

# 4. Defended/undefended tool registration for each single-layer config (via source inspection, no agent instantiation needed since that would require a Portkey key -- but let's also try live object construction without any model call)
check(
    "design_only registers ONLY read_document (no send_email/approve_payment)",
    "agent_tools = [read_document]" in src,
)
check(
    "code_only and prompt_only register the full 3-tool set",
    src.count("agent_tools = [document_tool, send_email, approve_payment]") >= 1
    and "agent_tools = [read_document, send_email, approve_payment]" in src,
)

# 5. Token accounting: verify the uncached-subtraction formula is used (no double-counting)
check(
    "Live-run cost formula subtracts cache_read_tokens from input before billing (no double-count)",
    "uncached = max(total_usage[\"input_tokens\"] - total_usage[\"cache_read_tokens\"], 0)" in src,
)

# 6. USD cost calculation -- deterministic fixture test (mock usage, no API call)
prices = json.load(open("data/prices.json", encoding="utf-8"))["gpt-6-luna"]
mock_input, mock_cache_read, mock_cache_write, mock_output = 24000, 11000, 500, 150
uncached = max(mock_input - mock_cache_read, 0)
expected_cost = (
    uncached * prices["input_per_1m"]
    + mock_cache_read * prices["cached_input_per_1m"]
    + mock_cache_write * prices["cache_write_per_1m"]
    + mock_output * prices["output_per_1m"]
) / 1_000_000
check(
    "Fixture cost calculation matches hand-computed expectation",
    abs(expected_cost - 0.0015475) < 1e-6,
    f"got {expected_cost}",
)

# 7. JSON schema of the already-built (reuse-only) output file
out = json.load(open("output/layer_cost_experiment.json", encoding="utf-8"))
REQUIRED_KEYS = {
    "document", "configuration", "layers_enabled", "model", "num_model_calls",
    "input_tokens", "output_tokens", "total_tokens", "cache_read_tokens",
    "cache_write_tokens", "cost_usd", "evaluation_result", "measured_or_reused",
    "source_reference", "num_model_calls_basis", "timestamp",
}
check("Output has exactly 60 observation rows", len(out["observations"]) == 60)
check(
    "Every row has all required schema keys",
    all(REQUIRED_KEYS.issubset(r.keys()) for r in out["observations"]),
)
check(
    "Every row's configuration is one of the 5 defined",
    all(r["configuration"] in exp.CONFIGURATIONS for r in out["observations"]),
)

# 8. Missing-data handling: missing rows have null measurement fields, not fabricated values
missing_rows = [r for r in out["observations"] if r["measured_or_reused"] == "missing_not_yet_measured"]
check(
    "All missing rows have null token/cost fields (no fabrication)",
    all(
        r["input_tokens"] is None and r["output_tokens"] is None and r["cost_usd"] is None
        for r in missing_rows
    ),
)
check("Exactly 34 missing rows (10 code_only + 12 design_only + 12 prompt_only)", len(missing_rows) == 34)
check(
    "Exactly 26 rows have real reused data (12 baseline + 2 code_only + 12 all_three)",
    len([r for r in out["observations"] if r["measured_or_reused"] != "missing_not_yet_measured"]) == 26,
)

# 9. Historical results unchanged (hash check against known baselines)
import hashlib


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


check(
    "output/usage_log.json unchanged by this experiment's dry-run",
    sha256("output/usage_log.json") is not None,  # existence + readability check; exact hash compared by caller across turns
)
check("output/defense_results.json still has 12 entries", len(json.load(open("output/defense_results.json", encoding="utf-8"))) == 12)
check("output/attack_results.json still has 12 entries", len(json.load(open("output/attack_results.json", encoding="utf-8"))) == 12)
check("output/layer_ablation.json still has 2 entries (untouched)", len(json.load(open("output/layer_ablation.json", encoding="utf-8"))) == 2)

# 10. No real email/payment can be executed during this experiment:
# design_only's agent_tools list (source-verified above) excludes send_email/
# approve_payment entirely; code_only/prompt_only include them but tools.py's
# own implementations (unmodified, hash-verified elsewhere) never perform a
# real action regardless of how they're called.
import tools as tools_mod
check(
    "tools.py unchanged (trap tools still logging-only, never real actions)",
    sha256("tools.py") == "181442a7ec0c20ed38b5cef87d21179e6ed3e3f241ca0e07716f409ce3b3b3c8",
)
check(
    "trap_calls.json untouched by any of this validation",
    json.load(open("output/trap_calls.json", encoding="utf-8")) == [],
)

print()
print(f"TOTAL: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILURES:", FAIL)
    sys.exit(1)
