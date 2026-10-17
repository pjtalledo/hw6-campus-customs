"""Problem 6: full DEFENDED-mode evaluation runner.

Runs agent.py --defense on against all 12 practice documents via the real
CLI (subprocess), same pattern as Problem 5's run_attack_tests.py, so the
original agent.py is only exercised through its public CLI contract.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON = str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")
TRAP_CALLS_PATH = PROJECT_ROOT / "output" / "trap_calls.json"

DOCS = [
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


def read_trap_calls() -> list:
    if not TRAP_CALLS_PATH.exists():
        return []
    try:
        data = json.loads(TRAP_CALLS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def main() -> None:
    results = []
    for doc in DOCS:
        doc_path = f"data/practice_docs/{doc}"
        trap_before = read_trap_calls()
        n_before = len(trap_before)

        proc = subprocess.run(
            [PYTHON, "agent.py", "--doc", doc_path, "--defense", "on"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            env={"PYDANTIC_AI_NO_BANNER": "1", **os.environ},
        )

        trap_after = read_trap_calls()
        new_trap_calls = trap_after[n_before:]

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

        results.append(
            {
                "document": doc,
                "status": status,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "structured_output": output_json,
                "new_trap_calls": new_trap_calls,
            }
        )
        print(f"[{doc}] status={status} trap_calls_triggered={len(new_trap_calls)}", file=sys.stderr)
        if new_trap_calls:
            print(f"  TRAP CALLS: {new_trap_calls}", file=sys.stderr)

    out_path = PROJECT_ROOT / "output" / "defense_raw_runs.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(results)} raw run records to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
