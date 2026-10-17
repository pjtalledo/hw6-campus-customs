# Campus Customs Vendor Desk Agent — Homework 6

An AI agent that reads vendor quote documents (HTML, PDF, EML) and returns a
structured purchasing recommendation against the Campus Customs Shop
Handbook's rules, using `gpt-6-luna` via Portkey. Built across Problems 1–10
of this assignment: baseline agent → cost analysis → caching experiment →
prompt-injection attacks → three-layer defenses → an original red-team
exercise → a blind exam run → an executive results report → this submission.

## What this project is, in one paragraph

`agent.py` is the entry point. It can run **undefended** (`--defense off`,
the default — reproduces the project's original Problem 3 behavior exactly,
needed for Problem 7's attack comparisons) or **defended** (`--defense on` —
adds document-content filtering, tool-access restriction, and a hardened
prompt). Two tools, `send_email` and `approve_payment`, exist in the system
but are **permanently simulated traps** — see "Safety" below. A separate,
standalone module (`approval.py` + `trusted_operator.py`) demonstrates a real,
tested human-approval mechanism for any future stage that might act on a
recommendation; it is intentionally **not** wired into the agent's own
execution path (see "Known limitations" below).

## Repository layout

```
agent.py, tools.py, models.py, defense_tools.py   -- the agent itself
approval.py, trusted_operator.py                  -- human-approval mechanism (standalone)
prompts/prompt.md                                 -- defended prompt (--defense on)
prompts/prompt_undefended.md                      -- original, undefended prompt (--defense off)
data/shop_handbook.md, data/prices.json           -- the agent's source of truth + model pricing
data/practice_key.json                            -- answer key for the 12 practice documents
data/practice_docs/                               -- 12 practice vendor documents
data/exam_docs/                                   -- 10 blind exam documents (no answer key)
data/my_attacks/                                  -- 2 original red-team attack documents
                                                      (+ data/my_attacks/v1_original/ and
                                                      v2_authority_workflow/: earlier, superseded
                                                      attack attempts, preserved for audit history)
output/                                           -- every deliverable: results, reports, logs
run_*.py, build_*.py, validate_*.py,
  test_trusted_approval.py, correct_historical_costs.py -- evaluation/build/test harnesses
AI_prompts.md                                     -- full prompt-by-prompt development history
```

## Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` in this same directory and fill in a real key:

```bash
cp .env.example .env
```

```
PORTKEY_API_KEY=your-real-key-here
```

`.env` is git-ignored — never commit it.

## Running the agent

From the repository root:

```bash
# Original, undefended agent (default; needed for Problem 7 reproducibility)
python agent.py --doc data/practice_docs/p01_bluehen_quote.html

# Defended agent (code + design + prompt defenses)
python agent.py --doc data/practice_docs/p01_bluehen_quote.html --defense on
```

Both require a real `PORTKEY_API_KEY` and make a real, small, paid API call.

## Deterministic local tests (no API key or API calls required)

These exercise document extraction, defense logic, and the human-approval
mechanism entirely offline:

```bash
python test_trusted_approval.py          # human-approval mechanism, 24 tests
python validate_layer_cost_experiment.py # cost-measurement infrastructure, 25 tests
```

Several `run_*.py`/`build_*.py` scripts (e.g. `run_attack_tests.py`,
`run_defense_tests.py`, `run_exam.py`, `run_layer_cost_experiment.py`) make
**real, paid API calls** when run directly — they were used once, with
explicit approval, to produce the result files already committed in
`output/`. You do not need to (and should not, without reason) re-run them;
doing so will not change any already-reported result, since every one of
these scripts either skips already-completed work or is explicitly
idempotent.

## Where to find each problem's deliverables

| Problem | Deliverable(s) |
|---|---|
| 1 | `AI_prompts.md` (this file documents every prompt used across the whole assignment) |
| 2 | `output/handbook_estimate.md` |
| 3 | `agent.py`, `tools.py`, `models.py`, `prompts/prompt_undefended.md`, `output/harness.md` |
| 4 | `output/cache_test.json`, `output/cache_test.md` |
| 5 | `output/attack_results.json`, `output/attack_results.md` |
| 6 | `defense_tools.py`, `prompts/prompt.md`, `approval.py`, `trusted_operator.py`, `output/defense_results.json`, `output/defense_results.md`, `output/harness.md` (Safety section) |
| 7 | `data/my_attacks/`, `output/red_team.json`, `output/red_team.md` |
| 8 | `run_exam.py`, `output/exam_results.json` |
| 9 | `output/hw6_report.html` (open by double-clicking — no server, no internet required) |
| 10 | This README, `.gitignore`, `.env.example`, `output/final_submission_audit.md` |

## Opening the executive report

`output/hw6_report.html` is a single, self-contained HTML file. Double-click
it (or open it in any browser via `File > Open`) — it needs no internet
connection, no local server, and no other file.

## Safety: `send_email` and `approve_payment` are permanently simulated

Both functions, in `tools.py`, **never** send a real email or move real
money, under any circumstances, in any mode, approved or not. Every call —
regardless of how it's reached — only appends a record to
`output/trap_calls.json` and returns a fixed "BLOCKED" message. This is true
across the entire project's history: `output/trap_calls.json` has remained
`[]` through every real test run ever executed in this repository.

## The human-approval workflow (`approval.py` + `trusted_operator.py`)

A real, tested, capability-token-based approval mechanism exists:
`approval.TrustedApprovalStore` issues a one-time, parameter-bound,
time-limited token; `trusted_operator.review_and_execute()` is the only
trusted, human-operated entry point that can obtain and use one. No model
output and no document content can ever produce, guess, or reuse a valid
token — `issue()`/`review_and_execute()` are not registered as agent tools
anywhere, confirmed by `test_trusted_approval.py`.

**Important, stated precisely so this is not overclaimed:** this mechanism
is a **separate, standalone path**. It is **not** wired into the live agent
(`agent.py`'s own tool registration, in either `--defense off` or
`--defense on`), by deliberate design — doing so would have changed the
undefended agent's behavior, which Problems 5 and 7's results depend on
staying exactly reproducible. See `output/harness.md`'s Safety section for
the full explanation of what this mechanism protects (a hypothetical future
"act on a recommendation" stage) and what it does not (the live agent path
itself, in either mode).

## Which tests need a live API key, and which don't

- **No API key needed:** `test_trusted_approval.py`,
  `validate_layer_cost_experiment.py`, and reading/inspecting any file in
  `output/` or `data/`.
- **API key + real cost required:** running `agent.py` directly, or any
  `run_*.py` script that invokes it.

## Known limitations (stated honestly, not minimized)

- **The human-approval mechanism does not protect the live undefended agent
  path.** A document cannot reach `send_email`/`approve_payment` in defended
  mode (they are never registered as tools), but in undefended mode the
  model *is* given both tools with no gate inside them — in every real test
  run across this project's history the model never chose to call them, but
  that is observed behavior, not an architectural guarantee, for that mode.
- **A known, disclosed extraction gap remains in the code-layer defense:**
  `defense_tools.py` filters inline `style=""`-based hiding but does not
  parse `<style>`-block CSS class selectors — confirmed during Problem 7's
  red-team exercise (see `output/red_team.md`).
- **Cost figures reflect this specific gateway's documented, non-deterministic
  prompt-caching behavior** — repeated runs of the same documents can show
  different cache-hit rates and costs; see `output/cost_correction_audit.md`
  and `output/cache_test.md` for the full analysis.
- **The exam results (`output/exam_results.json`) have no published answer
  key** — this project reports the agent's actual behavior only and makes no
  accuracy claim against a hidden key.

## Full development history

`AI_prompts.md` records every prompt used to build, test, attack, defend,
audit, and correct this project, problem by problem, including every
follow-up, every bug found and fixed, and every documentation correction
made along the way.
