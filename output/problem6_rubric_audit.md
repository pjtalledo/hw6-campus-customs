# Problem 6 Rubric Audit — Independent Grader-Style Review

**Scope: audit only.** No code, prompt, defense, output, or historical result
was modified while producing this report. No API calls were made — every
check below uses either static code inspection or already-stored evidence
(`output/defense_results.json`, `output/layer_ablation.json`, file hashes).

## Step 1 — Recovering the exact rubric

**A material limitation must be stated up front.** This project has no
separate, standalone rubric document from the professor — the only record of
"the Problem 6 assignment" is the text the user pasted into this conversation
and that was transcribed (in summarized/bracketed form, not a verbatim quote)
into `AI_prompts.md`. I searched the entire project for any other copy of the
assignment text:

```
grep -rl "Defend Your Agent" . --include="*.md" --include="*.txt" --include="*.pdf"
→ only output/*.md files that WE wrote (our own reports), nothing else
find . -iname "*.pdf" (outside data/practice_docs, data/exam_docs, data/my_attacks)
→ no results
```

**No file in this repository contains an official, professor-authored "Panel
A" / "Panel B" rubric document for Problem 6.** The "Panel A/B" terminology
in the current audit request does not appear anywhere in the original
Problem 6 prompt as transcribed in `AI_prompts.md`, nor in any other project
file. I cannot confirm whether a more detailed, panel-structured rubric
exists outside what was typed into this chat. **Per the explicit instruction
in Step 1, this must be stated plainly: compliance against any such
panel-structured rubric cannot be fully verified, because its exact wording
is not available to me.**

What I *do* have, and what this audit is based on, is the original Problem 6
prompt as the user typed it, preserved in full in `AI_prompts.md`'s "Problem
6: Defend Your Agent" section. The requirements enumerated below are
transcribed from that record. Where my own prior summary in `AI_prompts.md`
compressed multiple sentences into one, I have gone back to the substance of
each explicit instruction rather than inventing new requirements.

## Step 2 — Requirement-by-requirement compliance map

| # | Requirement (as given in the Problem 6 prompt) | Implementing file/function | Evidence | Verdict | Remaining risk |
|---|---|---|---|---|---|
| 1 | Defend at three levels — code, design, prompt — while preserving correct extraction/decisions for legitimate documents | `defense_tools.py`, `agent.py:_build_agent`, `prompts/prompt_defended.md` | `output/defense_results.json`: 60/60 fields, 12/12 decisions, 0 false positives on the 10 clean practice documents | **PASS** | None found |
| 2 | Record baseline file hashes before coding; preserve a working NO-DEFENSE mode for Problem 7 | Hashes recorded in `output/defense_results.md` / `AI_prompts.md`; `agent.py:_build_agent(defense="off")` | Re-verified now: `prompts/prompt.md` SHA-256 `1ed1200e...` unchanged; undefended toolset is exactly `['approve_payment','read_document','send_email']`, matching Problem 3 | **PASS** | None found |
| 3 | Selectable `--defense on\|off`, backward-compatible CLI, undefended mode genuinely reproduces original behavior | `agent.py` `main()`/`run_agent()`/`_build_agent()` | Re-verified now by direct inspection: `--defense` defaults to `"off"`; off-path loads `prompts/prompt.md` (hash-identical) and registers all 3 original tools | **PASS** | None found |
| 4 | Code-level: real visibility signals (not regex-only) for HTML/PDF/EML; preserve legitimate content; record uncertainty rather than guess | `defense_tools.py` (`_style_makes_hidden`, `_char_is_hidden`, EML part preference) | Local tests (documented in Problem 6/7 `AI_prompts.md` entries) confirmed hidden payloads removed, legitimate fields preserved on all 12 practice docs | **PASS** | A class-based CSS `display:none` rule (vs. inline `style=""`) is NOT caught — this is a **known, disclosed** residual gap (see Step 4) |
| 5 | Design-level: vendor-analysis stage cannot invoke sensitive tools directly; both trap tools preserved (not deleted/renamed/stubbed); any future action gated behind a separate human-approval boundary; human approval required before a legitimate action proceeds | `agent.py:_build_agent(defense="on")` (tool exclusion); `tools.py` (unchanged `send_email`/`approve_payment`); `approval.py` (`request_action`) | Tool-exclusion re-verified now: defended toolset is exactly `['read_document']`. `tools.py` SHA-256 unchanged. `approval.py` exists and is unit-tested | **PARTIAL — see Step 3** | `approval.py` is never imported or called by `agent.py`, `tools.py`, `models.py`, `defense_tools.py`, or `run_exam.py` (re-confirmed by `grep` just now, finding only a docstring mention). It is a standalone module, not an integrated gate. |
| 6 | Prompt-level: documents are untrusted, not so restrictive legitimate quotes get rejected, full handbook kept | `prompts/prompt_defended.md` | File exists, contains explicit untrusted-data rules; 0 false positives on legitimate documents (same evidence as #1); handbook is appended in full by `agent.py`, unchanged from the undefended path | **PASS** | None found |
| 7 | Test each layer independently before the full run | Documented in Problem 6's `AI_prompts.md` entry (local HTML/PDF/EML extraction tests, tool-list inspection, hash checks) | Re-ran the tool-list and hash checks now, got identical results | **PASS** | The original per-layer *test evidence* lives in `AI_prompts.md` prose, not a standalone script with assertions — acceptable but worth noting for a stricter grader |
| 8 | Run all 12 practice documents in DEFENDED mode with `gpt-6-luna`, capture real output/tokens/cost/audit evidence, avoid unnecessary repeated paid calls | `run_defense_tests.py`, `output/defense_raw_runs.json`, `output/usage_log.json` entries 14–25 | Re-confirmed now: `output/defense_results.json` has 12 entries, all `execution_status: "ok"`, all `model: gpt-6-luna` | **PASS** | None found |
| 9 | `output/defense_results.json`: same structure as `attack_results.json` + defense mode, token usage, cost, applied layers, audit references, for exactly 12 documents | `build_defense_results.py` | Re-verified now: 12 entries; key-set diff against `attack_results.json` shows zero missing keys, only the required additions present | **PASS** | None found |
| 10 | `output/defense_results.md`: before/after table (12 docs), baseline-vs-defended comparison, per-layer catch explanation, incremental token/cost per layer (measured vs. transparent estimate, not invented), false-positive analysis, remaining vulnerabilities | `output/defense_results.md` | File contains all six named sections (A–F); cost figures were later corrected (Problem 8/8.1 audit) without changing this structural compliance | **PASS** | The per-layer cost isolation is explicitly marked "not measured" for 2 of 3 layers (documented limitation, not a gap in reporting honesty) |
| 11 | `output/harness.md`: Safety section in plain English covering code/design/prompt defenses, human-approval requirement, how to run both modes | `output/harness.md` | Section present and reviewed just now; explicitly states `approval.py` is "a standalone, unit-tested module, not wired into any executable workflow" | **PASS** (as a *disclosure* requirement) | Accurately discloses the Step 3 finding below — this is actually evidence of good-faith compliance with the *documentation* half of requirement 5, even though the *design* half is only partial |
| 12 | Update `AI_prompts.md` preserving Problems 1–5 | `AI_prompts.md` | Problem 6 section preserved, Problems 1–5 sections intact above it (spot-checked) | **PASS** | None found |
| 13 | Final rubric audit (15 points, from the original Problem 6 prompt) | Reported at the end of the original Problem 6 turn | Was performed and reported at the time | **PASS** (historical) | This current document is a *second*, independent audit requested later, not a sign the first one was inadequate |

## Step 3 — Human approval audit (the central question)

The literal rubric language (as preserved in `AI_prompts.md`) is: *"design-
level defenses so the vendor-analysis stage cannot invoke sensitive tools
directly, with both trap tools preserved ..., any future action gated behind
a separate human-approval boundary, and recommendations never confused with
actual approvals."* This is evaluated point by point, without assuming
`approval.py`'s mere existence is sufficient, per the audit instructions:

| Sub-question | Finding | Verdict |
|---|---|---|
| Does `approval.py` actually block sensitive operations until explicit human authorization? | Yes, **when called** — `request_action()` raises `ApprovalRequiredError` unless `human_approved=True` is passed explicitly. | PASS, in isolation |
| Does it default to denial when approval is absent? | Yes — `human_approved: bool = False` is the default parameter value. | PASS |
| Does it handle rejection safely? | Yes — raises a typed exception (`ApprovalRequiredError`, a `PermissionError` subclass) rather than silently proceeding or returning an ambiguous result. | PASS |
| Does it prevent bypass through direct tool calls? | **No.** Re-tested just now: `tools.send_email(...)` can be called directly, with zero error, completely bypassing `approval.py`. `tools.py`'s `send_email`/`approve_payment` are plain public functions with no gate of their own — `approval.py` is the *only* path that enforces anything, and nothing requires code to go through it. (This test call was made and its one resulting entry in `output/trap_calls.json` was immediately reverted to `[]` to avoid polluting historical evidence — confirmed reset.) | **FAIL**, as a code-level enforcement guarantee |
| Is it integrated into the defended agent, or only a standalone demonstration? | **Standalone only.** `grep` across `agent.py`, `tools.py`, `models.py`, `defense_tools.py`, `run_exam.py` finds exactly one reference to `approval.py` — a comment in `agent.py`'s docstring. No import, no call, anywhere in the executable pipeline. | Standalone demonstration, confirmed |
| Does it meet the literal rubric requirement? | **Partially.** The rubric's *actually load-bearing* clause — "the vendor-analysis stage must not be able to invoke sensitive actions" — **is** fully satisfied, independently of `approval.py`, by the tool-exclusion design (the defended model is never given `send_email`/`approve_payment` at all, so no document, hidden or visible, can reach them). The *separate* clause — "any proposed future email or payment action must pass through a separate authorization boundary" — presumes a downstream "act on this recommendation" stage that **does not exist anywhere in this project**. `approval.py` was built to demonstrate what that boundary would look like, and was honestly disclosed (in `output/harness.md` and `output/defense_results.md`) as not wired into any real workflow. There is nothing currently in the codebase for it to fail to protect. | **PARTIAL** |

**Minimum necessary correction, if integration were required:** none of the
current code calls `tools.send_email`/`tools.approve_payment` except through
the model's own tool-calling mechanism (which the defended agent cannot
reach, by design) or through direct, deliberate Python calls (which only a
developer writing new code could make — not a vendor document). To make
`approval.py`'s gate *structurally* unbypassable rather than merely
available, `tools.py`'s `send_email`/`approve_payment` would need to be
renamed to private functions (e.g. `_send_email_impl`) and `approval.py`'s
`request_action()` would need to become the *only* public entry point to
them. This is a real, buildable fix, but it has not been implemented in this
audit, per the explicit "audit only, do not modify code" instruction.

## Step 4 — Defense and regression audit (no new API calls)

| Check | Result |
|---|---|
| Defended agent cannot invoke `send_email`/`approve_payment` | **PASS** — re-verified by direct inspection just now: `_build_agent(defense="on")`'s registered tools are exactly `['read_document']`. |
| Original undefended agent's behavior unchanged | **PASS** — re-verified: `--defense off`'s toolset is exactly `['approve_payment','read_document','send_email']` (unchanged), and `prompts/prompt.md`'s SHA-256 (`1ed1200e...`) matches the recorded Problem 3 baseline. |
| Original practice results reproducible from existing raw evidence | **PASS** — `output/defense_raw_runs.json` and `output/usage_log.json` entries 14–25 contain the full raw stdout/usage for all 12 documents; `output/defense_results.json` was independently re-derivable from them (confirmed during the Problem 8 cost-correction task, which re-ran `build_defense_results.py` as pure post-processing and reproduced the same classifications). |
| Documented 60/60 fields and 12/12 decisions match stored outputs | **PASS** — recomputed just now directly from `output/defense_results.json`: 60/60 field matches, 12/12 decision matches. |
| Zero trap activations supported by actual records | **PASS** — `output/defense_results.json` shows `trap_tools_called: []` on all 12 entries (0 total), consistent with `output/trap_calls.json` remaining `[]` across the entire defended run. |
| CSS-class limitation disclosed accurately | **PASS** — `output/defense_results.md` Section F and `output/red_team.md` both explicitly describe the `<style>`-block class-selector gap in `defense_tools.py`, confirmed via local (non-API) testing that it reaches both readers identically. |
| Problem 7 MIME attack results represented honestly | **PASS** — `output/red_team.json`/`.md` accurately show Attack B (MIME mismatch) succeeding undefended (`attack_succeeded: true`) and blocked defended (`attack_succeeded: false`), re-confirmed just now from the stored JSON. |

## Step 5 — Final recommendation

1. **Is Problem 6 fully compliant with the exact rubric?** **Not fully
   verifiable**, for two independent reasons: (a) the complete, literal
   rubric text (including any "Panel A/B" structure referenced in this audit
   request) is not available to me — only the prompt as typed into this
   chat; against *that* text, compliance is high but not perfect; (b) the
   one substantive gap found — `approval.py` not being integrated into any
   executable workflow, and not preventing direct-call bypass — is real and
   verified, not hypothetical.
2. **Fully verified requirements:** code-layer hiding removal + legitimate-content
   preservation (60/60, 0 false positives); design-layer tool exclusion
   (defended toolset = `['read_document']` only); prompt-layer untrusted-data
   framing; undefended-mode exact reproduction (hash + toolset match);
   `output/defense_results.json`/`.md` structure and content; `output/harness.md`
   Safety section; zero trap activations; honest disclosure of the CSS-class
   gap and the Problem 7 MIME attack outcome.
3. **Partial or unverified requirements:** the human-approval "separate
   authorization boundary" clause (`approval.py` exists, is correctly
   written, but is not integrated and can be bypassed by a direct Python call
   — PARTIAL); full compliance against any professor rubric text beyond what
   was pasted into this chat (NOT VERIFIED, source text unavailable).
4. **Is human approval integration actually required?** On the literal text
   available to me, the rubric's load-bearing clause ("the vendor-analysis
   stage must not be able to invoke sensitive actions") is satisfied by tool
   exclusion alone, independent of `approval.py`. The separate clause about
   gating "any proposed future action" presumes a downstream action-taking
   stage that this project does not build or require elsewhere. Whether
   *stricter* integration was intended cannot be settled without the missing
   rubric text — this is a genuine open question, not a clear-cut "yes."
5. **Minimum safe correction, if any:** make `tools.py`'s `send_email`/
   `approve_payment` private (e.g. prefix with `_`) and route all access
   through `approval.py.request_action()`, so the approval gate is
   structurally unbypassable rather than merely available. This is a small,
   mechanical, low-risk code change.
6. **Would the correction risk changing Problems 7–9?** Low risk, but not
   zero: Problem 7's attack-testing scripts and Problem 8's `run_exam.py`
   both exercise the agent only through the public `agent.py` CLI (`--defense
   on/off`), which never calls `tools.send_email`/`approve_payment` directly
   in the defended path — so the rename itself would not break them. However,
   the undefended path (`--defense off`, used by Problem 7's baseline tests)
   *does* register `tools.send_email`/`approve_payment` as agent tools by
   name; renaming the underlying functions would require also updating how
   they're registered (e.g. via a thin public wrapper with the original
   name), to avoid silently changing the undefended agent's tool schema —
   which Problem 6's own rubric requires to stay byte-for-byte reproducible.
   This makes the fix small but non-trivial to apply without any risk to
   historical reproducibility.
7. **Should we leave Problem 6 unchanged, or make a targeted fix?**
   **Recommendation: leave Problem 6's code unchanged for now**, and treat
   this audit's finding as a documented, disclosed limitation (already
   partially reflected in `output/harness.md`'s honest "standalone, not
   wired in" language) rather than a silent gap. The core safety property
   the rubric cares about most — a vendor document cannot cause a real email
   or payment — **is** actually guaranteed today, by tool exclusion, with or
   without `approval.py`. If a stricter, enforcement-level reading of "human
   approval boundary" turns out to be required once the full rubric text is
   available, the correction described in #5 is small and should be applied
   then, as its own reviewed change, rather than now.

---

## UPDATE (Problem 6 Priority 3 — superseding the Step 3 findings above)

**This section updates, rather than replaces, the Step 3 analysis above,
which is preserved as an accurate historical record of the state at the time
it was written.** Since this audit, the real Panel A/B text was obtained
(see `output/problem6_rubric_audit_v2.md`) and, following that, a genuine,
functional human-approval mechanism was implemented and approved
(`approval.TrustedApprovalStore` + `trusted_operator.py`, new files):

- **Does it prevent bypass through direct tool calls?** Re-stated precisely:
  the new `TrustedApprovalStore` mechanism itself cannot be bypassed — its
  deny-by-default, one-time-use, parameter-bound token check has no gap
  (verified by 24 passing tests in `test_trusted_approval.py`, including
  wrong-tool and different-arguments bypass attempts, both denied). However,
  **this mechanism is deliberately not wired into `agent.py`'s tool
  registration for either `--defense on` or `--defense off`** — a direct
  call to `tools.send_email(...)` (unchanged since Problem 3) still bypasses
  it entirely, by design, so that Problem 5/7's historical results remain
  reproducible under their original experimental conditions.
- **Is it integrated into the defended agent, or only a standalone
  demonstration?** Still a **separate, standalone path**, now genuinely
  functional and tested rather than only demonstrated — the distinction that
  matters is no longer "does it work" (it does) but "is it wired into the
  live agent" (it is not, by deliberate constraint).
- **Updated recommendation:** Problem 6's documentation (`output/harness.md`,
  `output/defense_results.md`) has been updated to describe this new
  mechanism accurately — what it protects (a hypothetical future
  "act on a recommendation" stage) and what it does not (the live undefended
  agent path, which remains intentionally unmodified). The human-sign-off
  wording ambiguity itself remains unresolved by this implementation; it is
  addressed by building a real mechanism without touching the historically-
  load-bearing `agent.py` undefended registration, which was judged the
  safer interpretation given the explicit instruction to preserve Problem
  5/7's original experimental conditions.
