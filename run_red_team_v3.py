import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON = str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")
TRAP_CALLS_PATH = PROJECT_ROOT / "output" / "trap_calls.json"

DOCS = [
    ("attack_a_mlm_classstyle.html", "data/my_attacks/attack_a_mlm_classstyle.html"),
    ("attack_b_wbc_mime_mismatch.eml", "data/my_attacks/attack_b_wbc_mime_mismatch.eml"),
]


def read_trap_calls():
    if not TRAP_CALLS_PATH.exists():
        return []
    try:
        data = json.loads(TRAP_CALLS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


results = []
for doc_name, doc_path in DOCS:
    for defense in ["off", "on"]:
        n_before = len(read_trap_calls())
        proc = subprocess.run(
            [PYTHON, "agent.py", "--doc", doc_path, "--defense", defense],
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
        r = {
            "document": doc_name,
            "defense_mode": defense,
            "status": status,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "structured_output": output_json,
            "new_trap_calls": new_trap_calls,
        }
        results.append(r)
        print(f"[{doc_name}] defense={defense} status={status} trap_calls={len(new_trap_calls)}", file=sys.stderr)
        if output_json:
            print(f"  output={output_json}", file=sys.stderr)

out_path = PROJECT_ROOT / "output" / "red_team_v3_raw_runs.json"
out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {len(results)} records to {out_path}", file=sys.stderr)
