#!/usr/bin/env python
"""Problem 8: run the final DEFENDED agent on all 10 exam documents.

Uses the EXISTING, unmodified production path -- the real agent.py CLI
(`python agent.py --doc <path> --defense on`), invoked once per file, exactly
as a human operator would. No model output is hand-edited, pre-filled, or
invented. There is no answer key for data/exam_docs/, so this script makes
no correctness judgment -- it only captures what the agent actually said.

Writes:
  output/exam_results.json      -- exactly one entry per file, the 13
                                    required fields, derived only from real
                                    API usage/tool-call evidence.
  output/exam_raw_runs.json     -- raw stdout/stderr/trap-call evidence per
                                    file, for independent audit, without
                                    changing the required submission format
                                    of exam_results.json itself.

Idempotent-by-default: if output/exam_results.json already has an entry for
a file, that file is SKIPPED on rerun (no duplicate paid calls) unless
--force is passed. This satisfies "avoid duplicate API calls caused by
accidental script reruns."
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON = str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")
EXAM_DOCS_DIR = PROJECT_ROOT / "data" / "exam_docs"
TRAP_CALLS_PATH = PROJECT_ROOT / "output" / "trap_calls.json"
RESULTS_PATH = PROJECT_ROOT / "output" / "exam_results.json"
RAW_RUNS_PATH = PROJECT_ROOT / "output" / "exam_raw_runs.json"


def read_trap_calls() -> list:
    if not TRAP_CALLS_PATH.exists():
        return []
    try:
        data = json.loads(TRAP_CALLS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def load_json_list(path: Path) -> list:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def run_one(doc_path: Path) -> dict:
    """Runs the real agent.py CLI, --defense on, on one document.

    Returns the raw evidence record (stdout/stderr/trap calls/usage) AND the
    13-field result record derived strictly from that evidence.
    """
    n_before = len(read_trap_calls())

    proc = subprocess.run(
        [PYTHON, "agent.py", "--doc", str(doc_path.relative_to(PROJECT_ROOT)), "--defense", "on"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        env={"PYDANTIC_AI_NO_BANNER": "1", **os.environ},
    )

    new_trap_calls = read_trap_calls()[n_before:]
    status = "ok" if proc.returncode == 0 else "error"
    output_json = None
    if status == "ok":
        stdout = proc.stdout.strip()
        try:
            start = stdout.rindex("{")
            output_json = json.loads(stdout[start:])
        except (ValueError, json.JSONDecodeError):
            output_json = None
            status = "error"

    raw_record = {
        "file": doc_path.name,
        "status": status,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "structured_output": output_json,
        "new_trap_calls": new_trap_calls,
    }

    # Pull the usage entry this run just appended to usage_log.json -- the
    # LAST entry, since agent.py appends synchronously before returning.
    usage_log = load_json_list(PROJECT_ROOT / "output" / "usage_log.json")
    usage_entry = usage_log[-1] if (status == "ok" and usage_log) else None

    if status != "ok" or output_json is None:
        result_record = {
            "file": doc_path.name,
            "vendor": None,
            "sku": None,
            "unit_price": None,
            "lead_time_days": None,
            "min_order": None,
            "decision": None,
            "reason": None,
            "trap_tool_called": len(new_trap_calls) > 0,
            "input_tokens": None,
            "cached_tokens": None,
            "output_tokens": None,
            "cost_usd": None,
            "execution_status": "error",
            "error": proc.stderr.strip()[-2000:] if proc.stderr else "Unknown failure; see output/exam_raw_runs.json.",
        }
        return raw_record, result_record

    cost_usd = usage_entry["cost_usd"]["total"] if usage_entry else None
    result_record = {
        "file": doc_path.name,
        "vendor": output_json.get("vendor"),
        "sku": output_json.get("sku"),
        "unit_price": output_json.get("unit_price"),
        "lead_time_days": output_json.get("lead_time_days"),
        "min_order": output_json.get("min_order"),
        "decision": output_json.get("decision"),
        "reason": output_json.get("reason"),
        "trap_tool_called": len(new_trap_calls) > 0,
        "input_tokens": usage_entry.get("input_tokens") if usage_entry else None,
        "cached_tokens": usage_entry.get("cache_read_tokens") if usage_entry else None,
        "output_tokens": usage_entry.get("output_tokens") if usage_entry else None,
        "cost_usd": cost_usd,
        "execution_status": "ok",
        "error": None,
    }
    return raw_record, result_record


def main() -> None:
    parser = argparse.ArgumentParser(description="Problem 8 exam runner")
    parser.add_argument(
        "--force", action="store_true",
        help="Re-run files that already have a result in output/exam_results.json "
             "(causes new paid API calls for those files).",
    )
    args = parser.parse_args()

    files = sorted(p for p in EXAM_DOCS_DIR.iterdir() if p.is_file())
    if len(files) != 10:
        print(f"WARNING: expected 10 files in {EXAM_DOCS_DIR}, found {len(files)}.", file=sys.stderr)

    existing_results = {r["file"]: r for r in load_json_list(RESULTS_PATH)}
    existing_raw = {r["file"]: r for r in load_json_list(RAW_RUNS_PATH)}

    results = []
    raw_runs = []
    for doc_path in files:
        fname = doc_path.name
        if fname in existing_results and not args.force:
            print(f"[{fname}] SKIPPED (already has a result; use --force to rerun)", file=sys.stderr)
            results.append(existing_results[fname])
            if fname in existing_raw:
                raw_runs.append(existing_raw[fname])
            continue

        print(f"[{fname}] running (defense=on) ...", file=sys.stderr)
        raw_record, result_record = run_one(doc_path)
        results.append(result_record)
        raw_runs.append(raw_record)
        print(
            f"  status={result_record['execution_status']} "
            f"decision={result_record['decision']} "
            f"trap_tool_called={result_record['trap_tool_called']} "
            f"cost={result_record['cost_usd']}",
            file=sys.stderr,
        )

    # Preserve exact filename order matching data/exam_docs/ directory order.
    order = {p.name: i for i, p in enumerate(files)}
    results.sort(key=lambda r: order.get(r["file"], 999))
    raw_runs.sort(key=lambda r: order.get(r["file"], 999))

    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    RAW_RUNS_PATH.write_text(json.dumps(raw_runs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(results)} entries to {RESULTS_PATH}", file=sys.stderr)
    print(f"Wrote {len(raw_runs)} raw evidence records to {RAW_RUNS_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
