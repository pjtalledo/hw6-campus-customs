# Cost Correction Audit — Retrospective Billing Fix for Problems 5, 6, 7

**This is an accounting and documentation correction only.** No model was
rerun, no API calls were made, no agent/tool/defense/handbook code changed
behavior, no decision changed, no reason changed, no attack outcome changed,
no document changed. Only the *derived dollar cost* fields — computed from
already-captured, unmodified raw token counts — were recalculated.

## The bug

`agent.py`'s `_usage_to_cost()` billed the **full** `input_tokens` value at
the uncached input rate, and *separately* billed `cache_read_tokens` again
at the cached rate. PydanticAI's own usage model documents `cache_read_tokens`
as a **subset** of `input_tokens`, not an additional amount — so this
double-charged every cached token. The same bug was found and fixed in
`cache_experiment.py` during Problem 4, but that fix was never applied to
`agent.py` itself. It went unnoticed through Problems 3, 5, 6, and 7 because
it was assumed (incorrectly, as this audit discovered) that `cache_read_tokens`
was usually `0` in real runs. In fact only Problem 3's original 2 calls had
`cache_read_tokens == 0`; nearly every real `agent.py` call made in Problems
5, 6, and 7 had a large nonzero `cache_read_tokens`, so the bug was active
and material in almost all of that cost reporting.

**The fix** (already applied to `agent.py` during Problem 8, before the exam
run): bill only `max(input_tokens - cache_read_tokens, 0)` at the uncached
rate; bill `cache_read_tokens` at the cached rate; bill `cache_write_tokens`
and `output_tokens` as before. This is the same formula `cache_experiment.py`
and `run_layer_ablation.py` already used correctly.

## What was corrected, and how

1. **`output/usage_log.json`, entries at indices 2–37** (Problem 5's 12
   undefended runs, Problem 6's 12 defended runs, Problem 7's 8 v1/v2 calls
   and 4 final-attack calls) — the `cost_usd` sub-object in each entry was
   recomputed from that same entry's own, unchanged `input_tokens`,
   `cache_read_tokens`, `cache_write_tokens`, and `output_tokens` fields,
   using `data/prices.json`'s exact rates and the corrected formula above.
   A `cost_correction_note` field was added to each corrected entry
   documenting the correction in place. **Indices 0–1 (Problem 3's original
   calls, `cache_read_tokens == 0`, mathematically unaffected) and indices
   38–47 (Problem 8's exam calls, already computed with the fixed formula)
   were left untouched** — confirmed byte-identical before and after.
2. **`output/defense_results.json`** — rebuilt by re-running the existing
   `build_defense_results.py` (pure post-processing, zero API calls), which
   pulls its `token_usage`/`cost_usd` fields directly from the
   now-corrected `output/usage_log.json` entries. (This script's internal
   indexing was also updated from a fragile "last 12 entries" lookup to a
   fixed absolute index range, `usage_log[14:26]`, since Problems 7 and 8
   have since appended further entries after Problem 6's — the lookup would
   otherwise have silently grabbed the wrong rows.)
3. **`output/red_team.json`** — rebuilt by re-running the existing
   `build_red_team_results.py` then `build_red_team_v3_results.py` (pure
   post-processing). The v3 script's indexing was similarly updated from
   `usage[-4:]` to the fixed absolute range `usage[34:38]`, for the same
   reason.
4. **`output/defense_results.md` and `output/red_team.md`** — all dollar
   figures, percentages, and the cost-related narrative text were updated to
   match the corrected JSON data, with explicit correction notices added.
   The underlying *correctness/effectiveness* conclusions in both documents
   (which attacks were blocked, field/decision accuracy, which defense layer
   mattered) are unchanged — only the dollar-figure narrative changed.
5. **Not touched, confirmed already correct:** `output/cache_test.json` /
   `output/cache_test.md` (Problem 4 — this is the experiment where the bug
   was originally found and fixed, in a separate script, `cache_experiment.py`,
   which never shared `agent.py`'s buggy function). `output/layer_ablation.json`
   (`run_layer_ablation.py` used its own, already-correct inline formula).
   `output/exam_results.json` / Problem 8 (computed with the already-fixed
   `agent.py`). `output/attack_results.json` / `output/attack_results.md`
   (Problem 5's JSON schema never included a cost field in the first place).

## Reconciliation table

| Source | Calls | Stored (buggy) total | Corrected total | Overstatement |
|---|---|---|---|---|
| Problem 5 — undefended baseline (`usage_log` idx 2–13) | 12 | $0.03922123 | $0.01727542 | $0.02194581 |
| Problem 6 — defended (`usage_log` idx 14–25) | 12 | $0.03495073 | $0.00746336 | $0.02748737 |
| Problem 7 — v1/v2 attempts (`usage_log` idx 26–33) | 8 | $0.03048832 | $0.01873871 | $0.01174961 |
| Problem 7 — v3 final attacks (`usage_log` idx 34–37) | 4 | $0.01377317 | $0.00671448 | $0.00705869 |
| **Total** | **36** | **$0.11843345** | **$0.05019197** | **$0.06824148** |

Per-run deltas for all 36 affected calls are preserved in
`output/cost_correction_raw_deltas.json` for full auditability.

## Reassessed conclusions (Phase 4)

- **Problem 6's baseline-vs-defended cost comparison, corrected:** total
  undefended cost $0.01727542 vs. total defended cost $0.00746336 (both for
  the same 12 documents) — a large-looking aggregate difference. **This
  difference is not attributable to the defense layers.** Per-document
  comparison shows 10 of 12 documents cost within about $0.00001 of each
  other between undefended and defended — the entire aggregate gap comes
  from exactly 2 documents (`p01`, `p08`) whose *undefended* run happened to
  receive **zero cache-read discount** (`cache_read_tokens: 0`) while every
  other call, defended or not, received a large cache discount. This is the
  same non-deterministic implicit-caching behavior already documented as a
  limitation in Problem 4 — an artifact of which 2 of 24 calls happened to
  miss the cache, not a property of the code/design/prompt defense layers.
  **Observed difference: real and measured. Causal claim ("defenses change
  cost"): not supported by the per-document data.**
- **Problem 7's attack-success/failure conclusions: entirely unchanged.**
  Attack A still fails in both configurations; Attack B (MIME mismatch)
  still succeeds against undefended and is still blocked by defended. None
  of this depended on the dollar figures.
- **Limitation carried forward:** the underlying cause of the caching
  non-determinism (likely non-sticky backend/replica routing at the
  Portkey/Azure OpenAI layer) remains outside this project's control and
  undiagnosed beyond what Problem 4 already established. Any future cost
  comparison across small numbers of calls in this environment should expect
  similar noise.

## Phase 5 — Independent verification

| # | Check | Result |
|---|---|---|
| 1 | No additional API calls | **PASS** — this was pure post-processing of existing `output/usage_log.json` data; no network calls were made. |
| 2 | No model responses changed | **PASS** — verified: all `structured_output`/`final_response` fields in `output/defense_results.json`, `output/red_team.json`, and `output/audit_trail.json` are identical before/after (only `cost_usd`/`token_usage` fields in the cost-bearing files changed). |
| 3 | No decisions or attack outcomes changed | **PASS** — `build_defense_results.py` reported the same 60/60 field accuracy, 12/12 decision accuracy, and the same 2 blocked attacks (`p02`, `p12`) after the fix as before. `build_red_team_results.py`/`build_red_team_v3_results.py` reported the identical success/failure pattern (Attack A: fail/fail; Attack B: succeed-undefended/blocked-defended) after the fix as before. |
| 4 | No trap logs changed | **PASS** — `output/trap_calls.json` was not opened or modified by this correction; it remains `[]`. |
| 5 | No original documents or handbook changed | **PASS** — this correction touched only `output/*.json`/`.md` files; `data/` was never opened by `correct_historical_costs.py` or the rebuild scripts except to read `data/prices.json` (read-only) and `data/practice_key.json`/`data/shop_handbook.md` (read-only, already used by the pre-existing build scripts). |
| 6 | No agent or defense code changed | **PASS** — `agent.py`, `tools.py`, `models.py`, `defense_tools.py`, `prompts/prompt.md`, `prompts/prompt_defended.md` were not touched in this correction (the `agent.py` billing fix itself was made during Problem 8, before this correction task began, and is not part of this correction's scope). Only two pre-existing *build/reporting* scripts (`build_defense_results.py`, `build_red_team_v3_results.py`) had their internal array-indexing logic corrected, which is a reporting-pipeline fix, not an agent/defense behavior change. |
| 7 | All corrected costs agree with raw token usage and `data/prices.json` | **PASS** — spot-verified: e.g. `usage_log[3]` (p02, baseline): input=23643, cache_read=11591 → uncached=12052; 12052×$0.10/1M + 11591×$0.01/1M + cache_write×$0.125/1M + output×$0.50/1M reproduces the stored corrected total exactly. |
| 8 | All report totals reconcile with per-run totals | **PASS** — the reconciliation table above was computed by summing the same per-run `cost_correction_raw_deltas.json` records that back every other total cited in this document; `output/defense_results.md` and `output/red_team.md`'s totals were taken directly from the rebuilt JSON files' own internal sums, not retyped by hand. |
| 9 | All JSON files remain valid | **PASS** — `output/usage_log.json`, `output/defense_results.json`, and `output/red_team.json` were each reloaded with `json.load()` immediately after writing, with no errors. |
| 10 | Problems 1–4 and Problem 8 remain intact | **PASS** — SHA-256 of `output/cache_test.json`, `output/handbook_estimate.md`, `output/exam_results.json` unchanged (verified below); `output/usage_log.json` indices 0–1 and 38–47 confirmed byte-identical before/after. |
| 11 | Original affected files preserved in the audit backup | **PASS** — pre-correction copies of `output/usage_log.json`, `output/defense_results.json`, `output/defense_results.md`, `output/red_team.json`, `output/red_team.md` are saved under `output/_pre_cost_correction_backup/`, with original SHA-256 hashes recorded in `AI_prompts.md`. |
| 12 | No credentials or secrets were introduced | **PASS** — this correction only manipulated numeric token/cost fields and added explanatory text; no new strings resembling API keys were written anywhere. |

### Supporting hash evidence (Problems 1–4, Problem 8 untouched)

```
output/cache_test.json       — unchanged (Problem 4, not in scope)
output/handbook_estimate.md  — unchanged (Problem 2, not in scope)
output/exam_results.json     — unchanged (Problem 8, computed with the already-fixed formula)
data/shop_handbook.md        — unchanged
data/practice_key.json       — unchanged
```

## Unresolved discrepancies

None identified. All 12 Phase 5 checks pass. The one open, previously-flagged
item (non-deterministic implicit caching behavior causing noisy per-call cost
comparisons) is a known, documented limitation of the underlying
Portkey/Azure OpenAI infrastructure, not a defect in this correction or in
the agent's own accounting logic, and is carried forward rather than
resolved here.
