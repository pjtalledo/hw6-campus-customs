# Homework 6 — Final Submission Audit (Problem 10, Phase 1–7)

**Status: audit complete. Repository NOT yet created or pushed. Awaiting
explicit approval before any GitHub action.**

---

## PHASE 1 — Requirement-by-requirement audit matrix

Source of truth: the actual Problem 1–9 prompts as transcribed verbatim (or
near-verbatim, bracketed where long) in `AI_prompts.md`, cross-checked
against real stored evidence. Where a sub-requirement's exact text was never
independently obtained from the professor (only typed into this chat), that
is noted rather than assumed resolved.

| # | Requirement (summarized; full text in `AI_prompts.md`) | Required output | Implementation | Verification evidence | Status | Unresolved risk |
|---|---|---|---|---|---|---|
| 1 | Document every prompt used across the assignment | `AI_prompts.md` | This file, maintained continuously | 160KB+ file, one section per problem, follow-ups documented | **PASS** | None |
| 2 | Estimate handbook token cost, with/without caching, formulas shown | `output/handbook_estimate.md` | tiktoken-based estimate, documented limitations | File exists, reviewed this session | **PASS** | Estimate explicitly labeled non-exact, as required |
| 3 | Build the agent: schema, tools, CLI, safety | `agent.py`, `tools.py`, `models.py`, `prompts/prompt_undefended.md` (originally `prompt.md`), `output/harness.md` | Built, tested, live-verified on p01/p08 at the time | `output/usage_log.json`/`audit_trail.json` indices 0–1; `output/harness.md` | **PASS** | None |
| 4 | Measure real caching cost (with/without), compare to Problem 2's estimate | `output/cache_test.json`, `output/cache_test.md` | 12 docs × 2 configs × 2 turns, real calls | Independently re-verified this session: without-cache $0.029399, with-cache $0.0545314, both exact | **PASS** | Caching behavior is gateway-specific and non-deterministic, disclosed in the report itself |
| 5 | Run practice set undefended, measure attack success | `output/attack_results.json`, `output/attack_results.md` | 12 docs, real calls | Re-verified this session: 58/60 fields, 10/12 decisions, 2 confirmed attacks (`p02`,`p12`) | **PASS** | None |
| 6 | Defend at 3 levels; preserve traps; preserve human sign-off mechanism; preserve undefended mode | `defense_tools.py`, `prompts/prompt.md`, `approval.py`, `trusted_operator.py`, `output/defense_results.json`/`.md`, `output/harness.md` | Code/design/prompt layers built; `prompts/prompt.md` literally holds defensive content (Priority 1 fix); `TrustedApprovalStore`+`trusted_operator.py` built and tested (Priority 3) | 60/60 fields, 12/12 decisions, 0 traps (re-verified); 24/24 approval tests pass (re-verified, clean env, this session); undefended toolset/prompt hash-identical to original | **PASS, with one disclosed, unresolved ambiguity** | **The human-approval mechanism is real and tested, but is NOT wired into the live agent path (`--defense off` or `on`), by deliberate design to preserve Problem 5/7 reproducibility.** Whether the literal rubric wording ("preserve the required human sign-off mechanism") requires live-path enforcement could not be conclusively determined even after obtaining the real Panel A/B text — see `output/problem6_rubric_audit.md` and its "UPDATE (Priority 3)" section. |
| 7 | Two original attacks, distinct from practice set, tested on/off defense | `data/my_attacks/`, `output/red_team.json`, `output/red_team.md` | `attack_a_mlm_classstyle.html` (CSS-class gap, confirmed real, unexploited by this payload), `attack_b_wbc_mime_mismatch.eml` (MIME mismatch, confirmed successful undefended, blocked defended) | Re-verified this session: both final attack files present; outcomes match `output/red_team.json` exactly | **PASS** | Attack A's underlying extraction gap remains open (disclosed, not claimed fixed) |
| 8 | Run defended agent on 10 blind exam docs, no answer key, no fabricated accuracy claims | `output/exam_results.json` | `run_exam.py`, 10/10 real calls | Re-verified this session: 10/10 present, 0 traps, independently recomputed costs match stored values exactly (0 mismatches across all 48 historical `usage_log.json` entries, including these 10) | **PASS** | `e05`'s model-generated reason contains a known, disclosed factual error (unrelated to any attack) — preserved unedited, as required |
| 9 | Self-contained offline HTML executive report | `output/hw6_report.html` | Single file, inline CSS/SVG, no externals | Re-verified this session: 0 external-resource matches via grep; opened via real headless-Chromium `file://` load (Problem 9's own session) with 0 console errors | **PASS** | None |
| 10 | Push to GitHub, submit URL | GitHub repo URL | **Not yet done** | This audit | **PENDING YOUR APPROVAL** | — |

**Special-attention items, as requested:**
- **Problem 6 human sign-off scope:** see row 6 above — the one substantive, honestly-unresolved ambiguity in this entire project.
- **Problem 7 original attack outcomes:** re-confirmed unchanged this session (`output/red_team.json` hash: `b4385c0a...`, matches its last-known value from before this audit began).
- **Problem 8 exam JSON schema / untouched model responses:** re-confirmed this session — all 13 required fields present on all 10 entries; independently recomputed costs match stored values with zero discrepancy; no field shows any sign of manual editing (cross-checked against `output/exam_raw_runs.json`'s raw stdout in earlier work).
- **Problem 9 standalone offline HTML:** re-confirmed this session via direct grep for external-resource patterns (zero matches) and file size (32,526 bytes, unchanged).

---

## PHASE 2 — Required repository structure

| Category | Required | Present? |
|---|---|---|
| ROOT | `AI_prompts.md` | ✅ |
| | `README.md` | ✅ (created this session) |
| | `.gitignore` | ✅ (created this session) |
| | `.env.example` | ✅ (created this session, placeholder only) |
| | `requirements.txt` | ✅ (pre-existing) |
| | `agent.py` | ✅ |
| | `tools.py` | ✅ |
| | `models.py` | ✅ |
| PROMPTS | `prompts/prompt.md` | ✅ — **confirmed this session to contain the defended prompt** (SHA-256 `3a6701c6...`, the defensive content, per the Priority 1 rubric fix) |
| DATA | `data/shop_handbook.md` | ✅ |
| | `data/prices.json` | ✅ |
| | `data/practice_key.json` | ✅ |
| | `data/practice_docs/` (12 docs) | ✅ — recounted this session: exactly 12 |
| | `data/exam_docs/` (10 docs) | ✅ — recounted this session: exactly 10 |
| | `data/my_attacks/` (2 final attacks) | ✅ — `attack_a_mlm_classstyle.html`, `attack_b_wbc_mime_mismatch.eml` present; **plus** `v1_original/` and `v2_authority_workflow/` subfolders preserving the two earlier, superseded attack attempts (additional audit evidence, not a substitute for the 2 required final files) |
| OUTPUT | All 14 explicitly listed files | ✅ — all present (see Phase 1 table); `output/red_team.json` also present (not explicitly listed by the professor but required by Problem 7's own spec, kept) |

**Confirmed: `prompts/prompt.md` contains the required defended prompt, while the original undefended prompt remains separately available at `prompts/prompt_undefended.md` for reproducibility** — exactly as required, re-verified this session via SHA-256 and by loading each file's content through `agent._build_agent()` for both modes.

**Additional Python files present (allowed per the instructions):** `defense_tools.py`, `approval.py`, `trusted_operator.py`, `cache_experiment.py`, `run_attack_tests.py`, `run_defense_tests.py`, `run_exam.py`, `run_layer_ablation.py`, `run_layer_cost_experiment.py`, `run_red_team_tests.py`, `run_red_team_v3.py`, `build_attack_results.py`, `build_defense_results.py`, `build_red_team_results.py`, `build_red_team_v3_results.py`, `correct_historical_costs.py`, `test_trusted_approval.py`, `validate_layer_cost_experiment.py`, `render_check.py`, `render_check_report.py` — all are real, previously-used evaluation/build/test harnesses referenced throughout `AI_prompts.md`, not dead or placeholder code.

---

## PHASE 3 — Security and packaging audit

| # | Check | Result |
|---|---|---|
| 1 | No `.env` committed | **PASS** — confirmed: no `.env` file exists anywhere inside this project directory (the real key lives in the course-root `.env`, one directory above, outside this project entirely, and was never copied in) |
| 2 | `.gitignore` excludes secrets/venvs/caches/temp files | **PASS** — created this session, excludes `.env`, `.venv/`, `__pycache__/`, `*.pyc`, OS/editor files, `*.tmp`/`*.bak`/`*.swp` |
| 3 | `.env.example` exists, placeholders only | **PASS** — contains only `PORTKEY_API_KEY=your-portkey-api-key-here` |
| 4 | No API keys/tokens/passwords/credentials in any staged file | **PASS** — re-scanned this session: `grep -rliE "portkey[_-]?api[_-]?key\s*[:=]\s*[a-zA-Z0-9]{10}|sk-[a-zA-Z0-9]{15,}"` across `output/`, every `.py`, and every `.md` file returned zero matches |
| 5 | No absolute machine-specific paths required for execution | **PASS** — `agent.py` resolves all paths relative to `Path(__file__).resolve().parent`; verified by running the entire test suite from a throwaway copy at a completely different absolute path (`/tmp/hw6_staging_check/hw6`) with no code changes needed |
| 6 | No virtual environment directories committed | **PASS** — `.venv/` excluded by `.gitignore`; confirmed not present in the 109-file staged list below |
| 7 | No unnecessary temporary files/screenshots/backups committed | **Reviewed, kept intentionally, not "unnecessary":** `output/hw6_report_desktop.png`/`output/hw6_report_mobile.png` (Problem 9's own required visual-verification evidence) and `output/render_evidence/*` (Problem 5's hidden-content visual verification evidence) are referenced as evidence in `AI_prompts.md` and are not disposable scratch files. `output/_pre_cost_correction_backup/` and `output/_pre_prompt_rename_backup/` are the explicit, required-by-instruction preservation of pre-change state for two separate correction tasks, directly cited as evidence in `output/cost_correction_audit.md` and `AI_prompts.md` — recommended to **keep**, not an accidental inclusion. |
| 8 | No private/unrelated personal documents | **One minor finding:** `AVAILABILITY.txt` (a one-line, pre-existing note: *"El sitio oficial no contiene enlaces de descarga para Homework 6 al 4 de septiembre de 2026."*) is unrelated to any graded deliverable. It contains no secret or personal information, but it is also not required. **Recommendation: exclude it from the publish whitelist** (see Phase 6). |
| 9 | Complete required `data/` folder present | **PASS** — re-verified counts this session (12 practice docs, 10 exam docs, 2 final attacks + 4 archived prior attempts, handbook, prices, key) |
| 10 | Final HTML has no external dependencies | **PASS** — re-verified this session via direct grep (zero matches for `http(s)://`, `<script src`, `<link rel="stylesheet"`, `cdn.`, `fonts.googleapis`, `<iframe`) |

**`AI_prompts.md` and raw logs specifically reviewed for accidentally-copied secrets:** scanned this session with the same pattern above (zero matches). No secret value is printed anywhere in this report.

---

## PHASE 4 — Reproducibility from a clean copy (actually executed, not assumed)

A separate staging directory (`/tmp/hw6_staging_check/hw6`, outside this project, with no access to the parent course directory's real `.env` and no copy of the existing `.venv`) was built from exactly the files intended for publication, and the following were run for real, in that clean copy:

| # | Check | Result |
|---|---|---|
| 1 | Fresh Python virtual environment created | **PASS** |
| 2 | `pip install -r requirements.txt` | **PASS** — zero errors |
| 3 | Python imports (`agent`, `tools`, `models`, `defense_tools`, `approval`, `trusted_operator`) | **PASS** — all import cleanly |
| 4 | Agent CLI, `--defense on/off` | **PASS** — `python agent.py --help` shows both options, `off` as default |
| 5 | Document extraction (practice files) | **PASS** — both `tools.read_document` and `defense_tools.read_document_defended` successfully read `p01_bluehen_quote.html` |
| 6 | Both agent toolsets | **PASS** — undefended `['approve_payment', 'read_document', 'send_email']`, defended `['read_document']`, both re-verified in the clean copy |
| 7 | Deterministic human-approval tests | **PASS** — `test_trusted_approval.py`: 24/24 passed in the clean environment |
| 8 | All required JSON files/schemas valid | **PASS** — 13 key JSON files re-parsed successfully in the clean copy (`usage_log.json`, `audit_trail.json`, `trap_calls.json`, `cache_test.json`, `attack_results.json`, `defense_results.json`, `exam_results.json`, `cost_correction_raw_deltas.json`, `layer_cost_experiment.json`, `layer_ablation.json`, `red_team.json`, `practice_key.json`, `prices.json`) |
| 9 | All 12 practice + 10 exam files present | **PASS** — recounted in the clean copy: 12 and 10 exactly |
| 10 | Both final red-team attack documents present | **PASS** |
| 11 | Historical output records internally consistent | **PASS** — field/decision counts recomputed from the clean copy's `attack_results.json`/`defense_results.json` match previously-reported figures exactly |
| 12 | Independent token-cost recalculation from stored usage data | **PASS — exhaustively, not a sample:** every one of the 48 entries in `output/usage_log.json` was independently recomputed from its own raw `input_tokens`/`cache_read_tokens`/`cache_write_tokens`/`output_tokens` fields and `data/prices.json`'s rates, using the corrected (non-double-counting) formula. **Zero mismatches** against the stored `cost_usd.total` values, across the entire history. |
| 13 | Corrected cost figures appear in all relevant reports | **PASS** — spot-checked `output/defense_results.md` for the corrected `$0.00746336`/`$0.01727542` figures, found present |
| 14 | Open `output/hw6_report.html` locally, no internet | **PASS** (previously performed with real headless-Chromium `file://` loads during Problem 9's own session, with 0 console errors and visual screenshots saved; re-confirmed this session only via static grep, not re-rendered, since nothing in the file changed) |
| 15 | No external resources required | **PASS** — re-verified by grep in the clean copy |

**No paid API calls were made during this entire Phase 4 verification.** Building the agent (`_build_agent()`) succeeded in the clean copy only because this specific shell session happens to have `PORTKEY_API_KEY` set as an ambient OS environment variable (confirmed: not from any file in this project — the key is not present in any committed file, per Phase 3 check #4); this is a property of the local machine's shell, not of the repository, and does not affect what would be published. No live model call (i.e., no call to `agent.run_agent()`/`agent.main()`) was made in this phase — only the no-network `_build_agent()` construction step and the already-approved historical calls from prior problems.

---

## PHASE 5 — README and grader experience

`README.md` (new, this session) was written to cover every item requested:
project understanding, setup/install, `.env` configuration via
`.env.example`, running both agent modes, reproducing deterministic local
tests (explicitly distinguishing which need a live API key and which don't),
a table locating every Problem 1–9 deliverable, how to open the HTML report,
the simulated-only nature of `send_email`/`approve_payment`, an explicit
explanation of the separate human-approval workflow and its scope, and a
dedicated "Known limitations" section that does not overstate security (it
names the live-path approval gap and the CSS-class extraction gap
explicitly). All commands are relative to the repository root; nothing
references the author's personal machine or accounts.

---

## PHASE 6 — Final staging audit

**Total files intended for publication (current working tree, excluding `.venv/`): 109**, minus the 1 recommended exclusion (`AVAILABILITY.txt`) = **108 files proposed for the public repository.**

**All required files present:** confirmed in Phase 2.
**All required data files present:** confirmed in Phase 2 and Phase 4.
**Forbidden files found:** **0** (no `.env`, no `.venv/`, no `__pycache__/`, no `.pyc`, no secrets).
**Secret scan result:** **0 matches**, across `output/`, every `.py` file, and every `.md` file (Phase 3, check 4).

**Exact relative paths:** the complete 109-file list was generated this
session via `find . -type f -not -path "./.venv/*"` and is reproducible by
running that same command from the project root; it is not reprinted in
full here to keep this report focused, but every file category is accounted
for in Phases 1–2 above, and the one recommended exclusion is named
explicitly (`AVAILABILITY.txt`).

**`output/usage_log.json` and `output/audit_trail.json` preserve the
complete relevant execution history:** confirmed — 48 entries each, spanning
Problem 3's original 2 calls through Problem 8's exam run, Priority 2's 34
new layer-cost observations are in a separate file
(`output/layer_cost_experiment.json`) by design (that live-execution path
intentionally does not write to `usage_log.json`/`audit_trail.json`, as
documented in `AI_prompts.md`), and nothing has been deleted or reset from
either file at any point in this project's history.

**Backups/temporary correction artifacts:** reviewed in Phase 3, check 7 —
recommended to **keep** both backup folders, as they are cited, necessary
evidence for the cost-correction and prompt-rename remediation work, not
accidental inclusions.

**No remaining failures identified in this audit.**

---

## PHASE 7 — Summary, before stopping for approval

### PASS/PARTIAL/FAIL per problem

| Problem | Status |
|---|---|
| 1 | PASS |
| 2 | PASS |
| 3 | PASS |
| 4 | PASS |
| 5 | PASS |
| 6 | PASS, with one disclosed, unresolved ambiguity (human sign-off scope) |
| 7 | PASS |
| 8 | PASS |
| 9 | PASS |
| 10 | PENDING — awaiting your approval to publish |

### Exact required-file checklist

All files listed in the professor's exact manifest (Phase 2 above) are
present and verified. `prompts/prompt.md` confirmed to hold the defended
prompt; `prompts/prompt_undefended.md` confirmed to hold the original,
byte-identical undefended prompt.

### Reproducibility results

All 15 Phase 4 checks passed in a genuinely clean, separate copy — including
an exhaustive, zero-mismatch independent recalculation of all 48 historical
API-cost records.

### Security findings

Zero secrets, zero forbidden files, zero machine-specific paths required.
One minor, non-security recommendation: exclude `AVAILABILITY.txt` as
unrelated to the graded deliverables.

### Unresolved rubric ambiguities

**Exactly one, carried forward honestly rather than resolved by assumption:**
Problem 6's "preserve the required human sign-off mechanism" — a real,
tested, standalone approval mechanism now exists (`approval.py` +
`trusted_operator.py`), but it is not wired into the live agent path, by
deliberate design to protect Problem 5/7 reproducibility. Full detail in
`output/problem6_rubric_audit.md`.

### Proposed public repository name

`campus-customs-vendor-desk-agent` (descriptive, matches the project's own
internal naming; avoids including the course number/personal name per
general good practice for a public repo, while remaining identifiable in a
submission context via the README's title and the Canvas submission note).

### Exact GitHub URL format to be used after publication

```
https://github.com/<your-github-username>/campus-customs-vendor-desk-agent
```

(To be filled in with the actual username at publication time — not created
yet.)

---

## STOP

**No GitHub repository has been created. Nothing has been pushed. Nothing
has been submitted to Canvas.** This document is the complete, actually-
executed audit requested for Problem 10, Phases 1–7. Awaiting your explicit
approval to proceed with repository creation and publication.
