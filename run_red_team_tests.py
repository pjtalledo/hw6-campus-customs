"""Problem 7: Red Team — run both original attacks under both defense modes.

Uses the real agent.py CLI (subprocess), exactly as Problems 5/6 did, so the
agent implementation is exercised through its public contract only.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON = str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")
TRAP_CALLS_PATH = PROJECT_ROOT / "output" / "trap_calls.json"

ATTACKS = [
    ("attack_a_harborview_quote.html", "data/my_attacks/attack_a_harborview_quote.html"),
    ("attack_b_bluehen_deposit_email.eml", "data/my_attacks/attack_b_bluehen_deposit_email.eml"),
]


def read_trap_calls() -> list:
    if not TRAP_CALLS_PATH.exists():
        return []
    try:
        data = json.loads(TRAP_CALLS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def run_one(doc_name: str, doc_path: str, defense: str) -> dict:
    trap_before = read_trap_calls()
    n_before = len(trap_before)

    proc = subprocess.run(
        [PYTHON, "agent.py", "--doc", doc_path, "--defense", defense],
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

    return {
        "document": doc_name,
        "defense_mode": defense,
        "status": status,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "structured_output": output_json,
        "new_trap_calls": new_trap_calls,
    }


def main() -> None:
    results = []
    for doc_name, doc_path in ATTACKS:
        for defense in ["off", "on"]:
            print(f"Running {doc_name} defense={defense} ...", file=sys.stderr)
            r = run_one(doc_name, doc_path, defense)
            results.append(r)
            print(f"  status={r['status']} trap_calls={len(r['new_trap_calls'])}", file=sys.stderr)
            if r["structured_output"]:
                print(f"  output={r['structured_output']}", file=sys.stderr)
            if r["new_trap_calls"]:
                print(f"  TRAP CALLS: {r['new_trap_calls']}", file=sys.stderr)

    out_path = PROJECT_ROOT / "output" / "red_team_raw_runs.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(results)} raw run records to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
