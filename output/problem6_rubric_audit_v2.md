# Problem 6 Rubric Audit v2 — Independent Validation Against Panel A / Panel B

**READ-ONLY AUDIT.** No code, prompt, or historical result was modified to
produce this report. No API calls were made. The one new piece of evidence
gathered (direct re-reading of `tools.py`'s function bodies) required no
execution of any sensitive action.

## Source text used

The requirements below are transcribed **verbatim** from the Panel A / Panel
B text supplied in this request. Per the explicit instruction, no obscured
or missing wording is invented or assumed — where the supplied text is
silent on a point, that is stated as "not specified in the supplied text,"
not filled in with a guess. This project still has no independent,
machine-readable copy of the original assignment (confirmed again: no PDF or
rubric file exists anywhere in the repository outside the practice/exam/
attack document sets), so this audit treats the user-supplied transcription
as the authoritative source, while noting that transcription accuracy from a
screenshot cannot itself be independently verified by this agent.

## Phase 1 — Fresh code inspection (not reused from the prior audit)

Re-read directly, just now, for this report:

- **`tools.py` lines 196–226** — `send_email(to, subject, body)` and
  `approve_payment(vendor, amount, currency="USD")`. Both: (a) take **no**
  approval/authorization parameter of any kind; (b) call `_append_trap_call`
  unconditionally; (c) return a fixed "BLOCKED" string; (d) perform no
  network call, no real action, regardless of who calls them or how. There is
  **no gate inside `tools.py` itself** — any gating exists only if a *caller*
  chooses to go through one.
- **`approval.py`** (full file, re-read) — `request_action(tool_name,
  arguments, *, human_approved=False)` raises `ApprovalRequiredError` unless
  `human_approved=True` is passed explicitly; if approved, it calls straight
  into `tools.send_email`/`tools.approve_payment`.
- **`agent.py`** — `grep -n "approval" agent.py` finds exactly one hit: a
  comment inside `_build_agent`'s docstring referencing `approval.py` as "the
  separate human-approval boundary." No `import approval`, no call to
  `approval.request_action` anywhere in `agent.py`.
- **`run_exam.py`, `run_attack_tests.py`, `run_defense_tests.py`,
  `run_red_team_tests.py`, `run_red_team_v3.py`** — none import or reference
  `approval.py`. None call `tools.send_email`/`tools.approve_payment`
  directly; they only ever exercise the system through `agent.py`'s CLI.
- **Entry points where `send_email`/`approve_payment` could execute:**
  (1) via a PydanticAI tool call from the model, only possible in
  `--defense off` mode, where `agent.py:_build_agent` registers
  `tools=[read_document, send_email, approve_payment]` directly (bare
  function objects, registered tool name = Python function name); (2) via
  direct Python code calling `tools.send_email(...)`/`tools.approve_payment(...)`
  — nothing prevents this from any module that imports `tools`.
- **`prompts/prompt.md`** (the undefended prompt) — re-read: contains "Never
  send emails or approve payments" as an instruction to the model, but this
  is a *model-behavior* instruction, not a code-level control.

## Phase 2 — Human approval requirement: direct answers

**A. Does the current architecture enforce human approval before sensitive
actions?** **No, not as a code-level control that cannot be bypassed.**
`tools.send_email`/`tools.approve_payment` contain zero approval checks of
their own (confirmed by direct reading, Phase 1). `approval.py` provides an
approval check, but only for callers who choose to go through
`approval.request_action()` — nothing requires that path.

**B. Can `send_email` or `approve_payment` be executed without authorization
through any supported execution path?**
- *Defended agent (`--defense on`):* **No** — the model has no tool object
  for either function; `_build_agent(defense="on")`'s `agent_tools` list
  contains only `read_document`. This was re-verified, not merely assumed,
  by instantiating the agent and reading its registered tool keys
  (`['read_document']`).
- *Undefended agent (`--defense off`):* **Yes, in principle** — both
  functions are registered as callable tools for the model, with no approval
  check inside them. In **every actual measured run across Problems 5–7**
  (confirmed from `output/trap_calls.json` remaining `[]` and
  `output/attack_results.json`'s `trap_tools_called` being empty on all 12
  documents, including two documents that explicitly tried to induce a tool
  call), the model never chose to call them — but that is **observed model
  behavior, not an enforced guarantee**. A sufficiently different prompt
  injection could, in principle, induce a call in undefended mode, and
  nothing in `tools.py` would stop it from "executing" (which, by design,
  only ever means logging — it can never send a real email or move real
  money, regardless of authorization).
- *Direct Python call, either mode:* **Yes** — re-confirmed in the prior
  audit session (one test call to `tools.send_email(...)` succeeded with no
  error, bypassing `approval.py` entirely; the resulting log entry was
  reverted). Not re-executed in this audit to honor "do not send emails or
  approve payments" / minimize redundant actions, but the code path is
  unchanged since that test and the finding stands on direct code reading
  alone (no approval check exists in `tools.py` to have been added or
  removed).

**C. Is tool isolation sufficient, or does the assignment additionally
require an integrated human-approval mechanism?** The supplied Panel A text
says: *"3. Preserve the required human sign-off mechanism."* This is phrased
as **preservation of an existing mechanism**, not as a new requirement to
*integrate* it into the live decision path. Two readings are both
textually defensible from the words given:
  - **Reading 1 (narrow):** "the required human sign-off mechanism" refers to
    the trap-tool pattern itself — `send_email`/`approve_payment` are
    built so that **no real action can ever occur without the trap being
    replaced by a real implementation**, which is itself a standing
    "nothing happens without further human/engineering action" control. Under
    this reading, "preserve" = don't delete or defang the traps, which is
    satisfied (confirmed: `tools.py`'s SHA-256 unchanged from the Problem 3
    baseline).
  - **Reading 2 (broader):** "the required human sign-off mechanism" refers
    specifically to a per-call authorization gate like `approval.py`, which
    must remain a meaningfully enforced control, not just present in the
    repository. Under this reading, since `approval.py` is never invoked by
    anything, "preserving" it as dead code arguably does not preserve a
    *mechanism* in any functional sense — only a demonstration of one.
  **This cannot be resolved from the text supplied.** Marking as **NOT FULLY
  VERIFIABLE** rather than guessing which reading the grader intends.

**D. Can the approval requirement be implemented without breaking the
undefended execution path required by Problem 7?** **Yes, with care.** The
undefended path's requirement (per Problem 6's original prompt, preserved in
`AI_prompts.md`) is that it "genuinely reproduces the original [Problem 3]
behavior" — concretely, that includes exposing tools literally named
`send_email` and `approve_payment` to the model (not renamed ones), since
Problem 7's attack-testing scripts and the model's own tool-calling rely on
those exact registered names, and `output/audit_trail.json`'s historical
`tool_name` field values are the string `"send_email"`/`"approve_payment"`
for comparability. The existing project already has a precedent for
preserving a public name while changing the underlying implementation:
`agent.py`'s defended path already does `Tool(read_document_defended,
name="read_document")`. The same pattern (`Tool(_send_email_impl,
name="send_email")`) would let the underlying function require approval
internally while keeping the externally-visible tool name, schema, and
calling convention unchanged.

**E. Does `approval.py` provide real enforcement, or is it currently only
unused supporting code?** **Currently only unused supporting code**, by the
plainest reading of "enforcement": a mechanism only enforces something if
something is required to go through it. Nothing is. It is correctly written
(verified: default-deny, typed rejection, no real-action capability even
when approved), but it enforces nothing today because it sits outside every
actual call path.

**F. Would making sensitive functions private or changing their registration
affect Problem 7 or existing tests?** Checked directly: `grep`-ing
`run_attack_tests.py`, `run_defense_tests.py`, `run_red_team_tests.py`,
`run_red_team_v3.py`, `run_exam.py`, and all four `build_*.py` scripts for
`send_email`/`approve_payment` finds only two references, both inside
**document content strings** describing what the *attack documents claim*
(not code that depends on the Python function name), plus one attack-name
label string. **No script programmatically depends on the literal function
name `send_email`/`approve_payment` in Python** — they depend only on the
CLI contract (`python agent.py --doc ... --defense off/on`) and on the
*registered tool name* seen in the model's tool-call output, which, if the
same `Tool(..., name="send_email")` wrapping pattern already used for
`read_document` is reused, would be preserved exactly. **Risk: low, with the
correct wrapping pattern; higher if the rename is done naively (e.g. without
re-wrapping to preserve the external name).**

## Phase 3 — Minimal correction proposal (NOT implemented; proposal only)

1. In `tools.py`: rename the two trap-tool function bodies to private
   implementations — `_send_email_impl(to, subject, body)` and
   `_approve_payment_impl(vendor, amount, currency="USD")` — keeping their
   internal logic (log to `output/trap_calls.json`, return the same "BLOCKED"
   message) byte-for-byte identical. Add two new thin public wrappers,
   `send_email(to, subject, body, *, human_approved: bool = False)` and
   `approve_payment(vendor, amount, currency="USD", *, human_approved: bool
   = False)`, each of which raises `approval.ApprovalRequiredError` unless
   `human_approved=True`, then delegates to the corresponding `_impl`
   function. (Equivalently, keep `tools.py` untouched and instead make
   `agent.py`'s undefended registration wrap `send_email`/`approve_payment`
   through `approval.request_action` via a small adapter closure — either
   placement achieves the same effect; the `tools.py`-level change is
   slightly more robust because it protects *every* caller, including direct
   Python imports, not just the one registered in `agent.py`.)
2. In `agent.py`'s undefended tool list: no change needed to tool names if
   wrapped as in (1) — `agent_tools = [document_tool, send_email,
   approve_payment]` continues to work unmodified, now calling the
   approval-gated public wrappers.
3. `approval.py` itself needs no change — it already implements deny-by-default,
   typed rejection, and delegates to the real (still-logging-only)
   implementations once approved.
4. This proposal satisfies the 10 stated constraints: preserves both trap
   tools (renamed internals only, same observable behavior); adds a real
   approval gate in front of them; denies by default; raises a distinct,
   catchable exception on rejection; a prompt-injected document still cannot
   bypass the gate, because the model's tool call would hit the new public
   wrapper and be denied by default (the model has no way to pass
   `human_approved=True` — that is not an exposed tool parameter a document
   could set); the undefended path's external tool names/schemas are
   unchanged, so Problem 7 remains reproducible; the defended path is
   unaffected (it never registers these tools at all); no historical JSON
   file would be touched by this change itself; no new third-party dependency
   is introduced; no real email/payment capability is added anywhere.

**This has NOT been implemented.** It is a proposal only, per the explicit
instruction to wait for approval.

## Phase 4 — Validation plan (to run only after approval, not now)

1. **Poisoned documents cannot trigger emails/payments:** rerun the existing
   local (no-API) HTML/EML hidden-content tests from Problem 5/6/7 against
   the *current* `tools.py` and confirm `output/trap_calls.json` stays
   unaffected by any local, non-model call to the renamed internals without
   `human_approved=True`.
2. **Sensitive actions without approval are blocked:** unit test —
   `tools.send_email(..., human_approved=False)` (or omitted) raises
   `ApprovalRequiredError`; same for `approve_payment`. No network/API call.
3. **Explicitly rejected actions remain blocked:** unit test — calling with
   `human_approved=False` explicitly (not just omitted) also raises; confirm
   no partial side effect occurs (e.g. `trap_calls.json` is not appended to
   on a rejected call, only on an approved-but-still-fake one, if that
   distinction is desired — to be decided before implementation).
4. **Legitimately approved actions proceed via a safe mock:** unit test —
   calling with `human_approved=True` reaches the `_impl` function and
   produces the same "BLOCKED"/logged behavior as today (still a safe trap,
   never a real action) — this is exercised entirely with local Python calls,
   no model, no network.
5. **Defended agent retains isolation:** re-run the existing, already-passing
   local check — `_build_agent(defense="on")`'s registered tools are exactly
   `['read_document']` — no change expected or needed.
6. **Undefended agent remains available for Problem 7:** re-run the existing
   local check — `_build_agent(defense="off")`'s registered tools are exactly
   `['read_document', 'send_email', 'approve_payment']`, with identical tool
   schemas (verify via PydanticAI's tool-definition introspection, comparing
   before/after).
7. **Clean documents continue returning valid quotes:** this specific change
   does not touch `read_document`, `defense_tools.py`, or any prompt file, so
   no new model call is logically required to verify this — but if full
   confidence is wanted, a small, explicitly-budgeted live re-run of a subset
   of clean documents could be proposed separately, with its own cost
   estimate and approval request.
8. **Historical results/artifacts unchanged:** diff SHA-256 of
   `output/attack_results.json`, `output/defense_results.json`,
   `output/red_team.json`, `output/exam_results.json`, and their `.md`
   counterparts before and after implementing the patch — none should change,
   since the patch only touches `tools.py`/`agent.py` source, not stored
   output.

None of the above was executed in this audit (Phase 4 is a **plan**, per the
instructions).

## Phase 5 — Requirement-by-requirement table (Panel A / Panel B, verbatim-sourced)

| # | Requirement | Source | Status | Evidence | File/function | Required action |
|---|---|---|---|---|---|---|
| A1a | Code-level defense: what the program does to the document before any model sees it | Panel A | **PASS** | `defense_tools.read_document_defended` strips CSS-hidden/off-page/white-text content before the model receives it; 60/60 fields correct, 0 false positives | `defense_tools.py` | None |
| A1b | Design-level: agent structured so a poisoned document cannot reach dangerous tools or influence the decision | Panel A | **PASS**, for the "cannot reach dangerous tools" clause (re-verified: defended toolset = `['read_document']` only) | Tool exclusion confirmed by direct inspection | `agent.py:_build_agent(defense="on")` | None |
| A1c | Prompt-level: defensive rules in `prompts/prompt.md` | Panel A | **PARTIAL — naming discrepancy** | The actual defensive rules were written to a **new file**, `prompts/prompt_defended.md`, not `prompts/prompt.md` (the original file is deliberately left untouched and still used by `--defense off`). Panel A's literal text names `prompts/prompt.md`. | `prompts/prompt_defended.md` vs. the literal path named in Panel A | Either confirm `prompts/prompt_defended.md` satisfies the intent (the design rationale — preserving `prompts/prompt.md` byte-for-byte for Problem 7 reproducibility — is sound and was explicit in the original Problem 6 prompt's broader text), or rename/duplicate to also literally satisfy the path `prompts/prompt.md` if the grader requires the exact filename |
| A2 | Do not delete `send_email` or `approve_payment` | Panel A | **PASS** | Re-read directly: both functions exist, unchanged, in `tools.py` (SHA-256 identical to Problem 3 baseline) | `tools.py` lines 196–226 | None |
| A3 | Preserve the required human sign-off mechanism | Panel A | **NOT FULLY VERIFIABLE** (ambiguous even in the unobscured text — see Phase 2C) | `approval.py` exists, is correct, is unmodified since Problem 6 — but is not invoked by any production path (re-confirmed by fresh `grep`) | `approval.py` (exists, unused); `tools.py` (no internal gate) | Needs the grader's clarification of which reading is intended; see Phase 3 for the fix if "enforced integration" is confirmed required |
| A4 | Keep a way to run without defenses (Problem 7 requires it) | Panel A | **PASS** | `--defense off` default; re-verified toolset `['read_document','send_email','approve_payment']` and `prompts/prompt.md` hash unchanged | `agent.py:main()`/`_build_agent()` | None |
| B5 | Rerun all 12 practice documents | Panel B | **PASS** | `output/defense_results.json` has exactly 12 entries, all `execution_status: "ok"` | `run_defense_tests.py`, `output/defense_results.json` | None |
| B6 | Same structure as Problem 5 + tokens/dollars per document | Panel B | **PASS** | Re-verified key-set diff: `attack_results.json` keys ⊆ `defense_results.json` keys, plus the required `token_usage`/`cost_usd`/`defense_mode`/`applied_defense_layers` additions, present on all 12 entries | `build_defense_results.py`, `output/defense_results.json` | None |
| B7 | Clean documents must return correct values | Panel B | **PASS** | 60/60 field matches, 12/12 decision matches, recomputed directly from `output/defense_results.json` | `output/defense_results.json` | None |
| B8 | Refusing/blank results for legitimate quotes counts as failure | Panel B | **PASS (no occurrence)** | All 12 entries have `execution_status: "ok"` and non-null structured output; zero refusals/blanks occurred | `output/defense_results.json` | None |
| B9a | `defense_results.md`: before-and-after table, all 12 documents | Panel B | **PASS** | Section A of `output/defense_results.md` contains the full 12-row table | `output/defense_results.md` | None |
| B9b | What each defense layer catches that the others miss | Panel B | **PASS** | Section C of `output/defense_results.md` addresses this explicitly, with the controlled ablation evidence for the code layer | `output/defense_results.md` | None |
| B9c | Additional tokens and dollars introduced **by each defense layer, per document** | Panel B | **PARTIAL/FAIL against the literal text** | `output/defense_results.md` Section D explicitly states the per-layer-per-document cost is **not measured** for the design and prompt layers (only an aggregate 12-document before/after, plus a 2-document code-layer-only ablation) | `output/defense_results.md` Section D | If graded literally, this is a real, already-disclosed gap: full per-document, per-layer cost attribution (3 layers × 12 documents) was never produced, because isolating each layer independently would require ~3× more paid API calls than were spent, and this was deliberately not done to control cost (as documented at the time) |
| B10 | `harness.md` Safety section, plain-language explanation of each defense layer | Panel B | **PASS** | Section present, covers code/design/prompt/human-approval/how-to-run, and explicitly discloses `approval.py`'s non-integration | `output/harness.md` | None |

## Final assessment

1. **Overall Problem 6 compliance:** **Mostly compliant, with two concrete,
   literal-text gaps** — (a) the defensive prompt was written to
   `prompts/prompt_defended.md`, not the literally-named `prompts/prompt.md`;
   (b) per-document, per-layer token/dollar attribution (Panel B item 9's
   third bullet) was not fully produced, and this was already disclosed as a
   limitation rather than hidden. The human-sign-off question (Panel A item
   3) is **genuinely ambiguous** even with the now-available text and cannot
   be marked PASS or FAIL with confidence without clarification.
2. **Is a code correction truly required?** **Not certain** — it depends on
   which reading of "preserve the required human sign-off mechanism" is
   intended (Phase 2C). If the grader intends enforced, integrated approval,
   then yes, a correction is required. If "preserve" means "don't remove the
   trap-tool/approval-module pattern that already exists," then arguably no
   code change is required, only clearer documentation of what exists.
3. **Minimal proposed patch, if necessary:** as detailed in Phase 3 —
   wrap `tools.send_email`/`tools.approve_payment` behind a `human_approved`
   parameter that defaults to `False` and raises `ApprovalRequiredError`
   otherwise, preserving the external tool name/schema via the same
   `Tool(..., name=...)` pattern already used for `read_document_defended`.
4. **Potential regression risks:** low if the `Tool(name=...)` wrapping
   pattern is used (external name/schema preserved); moderate if the rename
   is done naively (would silently change the undefended agent's tool schema
   and break Problem 7/8's reproducibility and historical `tool_name` string
   comparability).
5. **Exact tests needed after approval:** the 8 items listed in Phase 4,
   items 2–4 and 5–6 require no new API calls at all (pure local unit tests);
   item 7 could be verified without new calls if judged unnecessary, or with
   a small, separately-budgeted live re-run if extra confidence is wanted;
   item 8 is a pure hash-diff check.
6. **Impact on Problem 7:** none expected if the wrapping pattern above is
   used — Problem 7's attack scripts depend only on the CLI contract and the
   registered tool name, neither of which would change.
7. **Can Problem 6 be safely closed?** **Not with full confidence yet** —
   recommend obtaining clarification on Panel A item 3's intended scope
   (narrow "preserve what exists" vs. broad "integrate enforced approval")
   before declaring final compliance, and deciding whether the
   `prompts/prompt.md` vs. `prompts/prompt_defended.md` naming discrepancy
   needs a literal-path fix. Both are small, well-understood open items, not
   evidence of a broken implementation — the core safety property (no real
   email/payment can ever occur, and the defended agent cannot reach the
   trap tools at all) holds today regardless of how these two items are
   resolved.

**No changes have been made. Awaiting explicit approval before implementing
anything in Phase 3.**
