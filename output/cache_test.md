# Problem 4 — With and Without Cached Tokens (CORRECTED)

**This document supersedes the earlier version of `cache_test.md`.** The
`with_cache` / `without_cache` labels used in the first analysis were
backwards relative to what their configurations actually do, per OpenAI's own
SDK documentation (Section 5). The underlying experiment — the same 48 real
model calls — was not rerun; only the setup labels were corrected, with full
traceability preserved in `output/cache_test.json` (each record keeps both
`setup` (corrected) and `original_setup_label` (as first recorded), plus a new
`cache_mode` field naming the actual technical configuration).

All figures below are computed directly from `output/cache_test.json`
(`phase: "full"` records only — 48 real model calls: 12 documents × 2 setups ×
2 turns each). No token counts, cache activity, or costs are estimated,
invented, or recalculated from anything other than the original API responses.

## 1. Objective and methodology

Measure whether prompt caching produces a verifiable, measurable cost change
for the Campus Customs vendor desk agent (Problem 3), by running the same 12
practice documents through the same agent (same `gpt-6-luna` model, same full
handbook, same instructions, same tools, same `VendorRecommendation` schema,
same purchasing rules) under two caching configurations, and comparing actual
API-reported token usage and cost.

`cache_experiment.py` reuses Problem 3's building blocks (`agent.py`'s prompt
loading, pricing, and credential logic; `models.py`; `tools.py`) without
modifying any Problem 3 file, and writes only to `output/cache_test.json` /
`output/cache_test.md`. Problem 3's own CLI and logs (`output/usage_log.json`,
`output/audit_trail.json`) are untouched.

## 2. The two caching setups (corrected)

| Setup | Technical configuration | What it actually does |
|---|---|---|
| **`with_cache`** | Default model settings — **no** `openai_prompt_cache_options` override — plus a single stable `openai_prompt_cache_key` shared across all 12 documents | OpenAI's implicit, automatic prompt caching is **active**. This is the only configuration in this project that produced real `cache_read_tokens > 0`. |
| **`without_cache`** | `openai_prompt_cache_options(mode="explicit", ttl="30m")`, no manual cache breakpoints added, a fresh random `openai_prompt_cache_key` per document | Per OpenAI's own SDK documentation, `mode="explicit"` **disables the implicit cache breakpoint** unless the caller manually inserts breakpoints (this project never does). Verified **reliably zero-read** across every call made under this configuration. |

Both setups used identical prompt content, document set, tools, and output
schema; the only intentional difference is the cache-mode/key configuration
above.

## 3. Evidence from actual API token usage

| Setup | Documents | Model calls | Calls with `cache_read_tokens > 0` | Total `cache_write_tokens` | Total `cache_read_tokens` |
|---|---|---|---|---|---|
| `with_cache` | 12 | 24 | **4** | 234,206 | 46,365 |
| `without_cache` | 12 | 24 | **0** | 0 | 0 |

**`with_cache`: cache reuse IS VERIFIED, but only partially.** 4 of the 12
documents (`p01_bluehen_quote.html`, `p06_qtextile_quote.pdf`,
`p08_chapelst_email.eml`, `p09_westville_email.eml`) showed a nonzero
`cache_read_tokens` on their own turn 2, reading back the cache their own
turn 1 had just written:

| Document | Turn 1 `cache_write_tokens` | Turn 2 `cache_read_tokens` |
|---|---|---|
| p01_bluehen_quote.html | 11,590 | 11,590 |
| p06_qtextile_quote.pdf | 11,591 | 11,591 |
| p08_chapelst_email.eml | 11,592 | 11,592 |
| p09_westville_email.eml | 11,592 | 11,592 |

The other 8 of 12 documents wrote to cache on both turns but never read from
it — the implicit, automatic caching behavior is real but inconsistent at this
scale (see Section 8). **Reuse is verified** (the "at least one relevant call"
bar is clearly met, 4 times over), but it is **not reliable or complete**
across all 12 documents.

**`without_cache`: zero cached reads, confirmed on every single call.** All 24
calls under the explicit-mode configuration reported `cache_write_tokens=0`
and `cache_read_tokens=0` — no caching activity of any kind. This matches
every diagnostic call made under this configuration throughout Problem 4 (37
total calls across all rounds, 0 exceptions).

**Caching requested vs. caching achieved, summarized:**

| Setup | Caching requested | Caching achieved |
|---|---|---|
| `with_cache` | Implicit/automatic reuse of the handbook/instructions prefix | Partially achieved — real reads on 4/12 documents, no reads on the other 8/12 |
| `without_cache` | No caching (explicit mode, no breakpoints) | Fully achieved — zero cache activity on all 24 calls |

## 4. Total cost and cost per document

Costs use `data/prices.json` rates for `gpt-6-luna` (input $0.10/1M, cached
input $0.01/1M, cache write $0.125/1M, output $0.50/1M), applied per call to
the **uncached** portion of input tokens only (`total_input_tokens −
cache_read_tokens`, to avoid double-counting the cached portion — see
Section 9) plus the cached-read, cache-write, and output tokens at their own
rates, summed unrounded and rounded only for display here.

| Setup | Total cost (12 docs, 24 calls) | Average cost per document |
|---|---|---|
| **`without_cache`** (caching disabled) | **$0.029399** | **$0.0024499** |
| **`with_cache`** (caching enabled, partial reuse) | **$0.0545314** | **$0.0045443** |

## 5. SDK evidence for the corrected interpretation

The OpenAI Python SDK installed in this project's `.venv`
(`openai/types/chat/completion_create_params.py`, and the equivalent
`responses` module) documents `PromptCacheOptions.mode` as follows (exact
text):

> "By default, OpenAI automatically chooses one implicit cache breakpoint. You
> can add explicit breakpoints to content blocks with
> `prompt_cache_breakpoint`. ... **Set `mode` to `explicit` to disable the
> implicit breakpoint.** The `ttl` defaults to `30m`..."

This project never adds manual `prompt_cache_breakpoint` markers (PydanticAI's
`CachePoint` feature) to the handbook/instructions content. That means setting
`mode="explicit"` — with no manual breakpoints to replace the one it just
disabled — **removes the only caching mechanism this project's calls would
otherwise use**. This is an exact, independently-documented explanation for
why that configuration showed `cache_write=0, cache_read=0` on literally every
call made under it (37/37 across all diagnostic rounds and the full
experiment): it isn't a gateway quirk or a flaky backend — it is explicit
mode behaving exactly as OpenAI's own documentation says it will, given that
no explicit breakpoints were supplied.

Separately, PydanticAI's own model-profile logic
(`pydantic_ai/profiles/openai.py`) further restricts its explicit-breakpoint
feature (`CachePoint` → `prompt_cache_breakpoint`) to model names starting
with `gpt-5.6` or `gpt-6-astra`. `gpt-6-luna` matches neither prefix, so even
if this project had added manual breakpoints, PydanticAI's library code would
not have emitted them for this model name — a second, independent reason the
explicit-mode configuration could never have produced caching here.

Given this, the configuration with **no override** (OpenAI's default,
implicit, automatic caching) is the one that engages caching — confirmed by
it being the only configuration that ever produced `cache_read_tokens > 0` in
this project's testing — and is therefore correctly labeled `with_cache`.

## 6. The cost difference: caching increased cost here

**Additional cost from caching, measured:** $0.0545314 − $0.029399 =
**$0.0251324** over 12 documents.

**Percentage, relative to the uncached (`without_cache`) baseline:**
$0.0251324 / $0.029399 = **85.49% more expensive**.

**This must be stated plainly: in this experiment, enabling caching
increased cost. It did not save money.** The reason is visible directly in
the token totals (Section 3): `with_cache` paid the cache-write surcharge
($0.125/1M, 25% more than the $0.10/1M plain uncached input rate) on every one
of its 24 calls — 234,206 cache-write tokens in total — while only 46,365 of
those tokens ever came back as a cheaper cached read ($0.01/1M). **The cache
reads that did occur were real, but far too small and far too infrequent (4
of 12 documents, not all 12) to offset the cache-write surcharge paid on every
call.** `without_cache`, by contrast, paid a flat, simple uncached-input rate
with no write surcharge at all, which is why it ended up cheaper despite
achieving zero caching.

**We do not represent this as a caching success.** The experiment verifies
that cache reuse is technically possible with this configuration (Section 3),
but also verifies, with the same data, that — at the API's current write/read
pricing and this project's actual hit rate — using it was more expensive, not
less, than not caching at all.

## 7. Comparison against Problem 2

`output/handbook_estimate.md` (Problem 2) estimated the handbook alone at
~10,058 tokens (local `tiktoken` estimate) and a single uncached call costing
~$0.0010058.

Both of this experiment's real, measured, full-agent per-document costs
(~$0.0024 without_cache, ~$0.0045 with_cache) are substantially higher than
that handbook-only estimate (roughly 2.4×–4.5×), for reasons visible directly
in this experiment's data and not present in Problem 2's simplified model:

- **Repeated handbook transmission across turns:** each document run is 2
  model turns, and the chat-completions API resends the full system prompt
  (instructions + handbook) on *every* turn — Problem 2 only priced one copy.
- **Additional prompt/tool-schema overhead:** actual per-turn total input is
  ~11,700–11,940 tokens, noticeably above the ~10,844 tokens Problem 2's
  components would predict (instructions 786 + handbook 10,058) — the
  difference is the JSON schemas for the 3 registered tools and the
  structured output type, which Problem 2 did not model at all.
- **Cache writes vs. cache reads:** Problem 2 assumed a clean "write once,
  read many" caching model that straightforwardly reduces cost. This
  experiment shows the real picture is messier: cache *writes* happen on
  (almost) every call under the caching-enabled configuration, while verified
  cache *reads* only happened for 4 of 12 documents — not enough to offset the
  write cost, let alone produce the savings Problem 2's model implicitly
  assumed.
- **Output tokens:** Problem 2 only considered handbook input cost; this
  experiment also bills ~75–120 output tokens per turn, which Problem 2 did
  not include at all.

**Problem 2's handbook-only estimate and this experiment's full-agent cost are
not measuring the same quantity** — the former is a single-prompt token
estimate; the latter is the actual, multi-turn, tool-using, schema-carrying
cost of one real document evaluation, now further complicated by caching
behaving inconsistently and, in this case, adding cost rather than removing
it.

## 8. Projection for 1,000 documents/day × 30 days (30,000 documents)

Using the corrected, observed average cost per document from Section 4, held
constant:

| Setup | Per day (1,000 docs) | 30 days (30,000 docs) |
|---|---|---|
| `without_cache` (caching disabled) | $2.4499 | **$73.50** |
| `with_cache` (caching enabled, partial reuse) | $4.5443 | **$136.33** |

**Assumptions (explicitly stated, since this is a projection, not a
guaranteed billing amount):**
- 2 model calls (turns) per document, matching every run observed in this
  experiment (1 tool call, then 1 final structured response).
- Token usage per document stays close to what was observed here (~11,700–
  11,940 input tokens/turn, ~75–120 output tokens/turn); the 12 practice
  documents are short, simple quotes/emails, and real vendor documents at
  scale could be longer or more varied, which would raise costs.
- The handbook and agent instructions remain unchanged in content and length
  over the 30-day period — any handbook growth would raise per-call input
  tokens for both setups.
- For `with_cache`, the projection assumes the same ~33% (4/12) incidental
  cache-hit rate observed in this small 12-document sample continues at
  scale — an uncertain extrapolation. A different (higher or lower) real hit
  rate at 30,000 documents could change whether caching remains more
  expensive, becomes cost-neutral, or eventually becomes cheaper than
  `without_cache`; this experiment cannot determine that threshold.
- No retries, rate-limit backoff, or failed-call costs are included.

This is a **projection**, not a guaranteed invoice: actual Portkey/Azure
billing could differ based on gateway routing, pricing changes, retries, or
changes to the handbook/instructions. **At the hit rate actually observed,
the projection shows caching costing roughly $62.83 more than not caching**
over 30,000 documents ($136.33 − $73.50), consistent with Section 6.

## 9. Surprising findings

1. **The setup intended to enable caching (`with_cache`, via explicit
   breakpoint mode) was the one that reliably disabled it**, and the setup
   intended only to avoid cross-document reuse (`without_cache`, via
   per-document unique keys under the default/implicit mode) was the one that
   actually engaged real caching. This was discovered by reading the
   installed OpenAI SDK's own docstring (Section 5), not by further live
   experimentation — a configuration/interpretation error on our part, now
   corrected with the existing data (no new API calls needed).
2. **Caching, where it did occur, was inconsistent across otherwise-identical
   requests.** All 12 documents share byte-for-byte the same system prompt
   (instructions + handbook). 4 of 12 got a same-document cache hit on turn 2;
   the other 8 did not. This points to non-deterministic, backend-dependent
   caching (e.g. a gateway or Azure OpenAI deployment load-balancing requests
   across multiple backend replicas, each keeping its own local, unshared
   prompt cache, so whether a given pair of calls lands on the same replica —
   and thus can share a cache — appears to be a matter of chance).
3. **Caching made this workload more expensive, not cheaper.** This is the
   opposite of the usual assumption that prompt caching reduces cost. It did
   here because cache-write tokens are priced *above* plain uncached input
   ($0.125/1M vs $0.10/1M) and the observed read rate (4/12 documents) wasn't
   high enough to recover that premium.
4. **Total input tokens were identical between the two setups** (283,595
   tokens each) — confirming the two setups really did send equivalent
   prompts and only differed in cache behavior, as required for a fair
   comparison.

## 10. Limitations and reproducibility

- **A real cost-calculation bug was found and fixed earlier in this
  investigation**: the first implementation of `_usage_to_record()` in
  `cache_experiment.py` billed the *full* `input_tokens` at the uncached rate
  *and* separately billed `cache_read_tokens` at the cached rate.
  PydanticAI's own usage documentation (`pydantic_ai/usage.py`) states
  `cache_read_tokens` is a *subset* of `input_tokens`, not additive, so this
  double-charged the cached portion. Fixed by pricing
  `(total_input_tokens − cache_read_tokens)` at the uncached rate. This fix
  was applied to all records using their already-captured raw token counts —
  no new API calls were made for it, and it remains in effect for the figures
  in this corrected document.
- **The setup-label correction described in this document was also applied
  without any new API calls** — only the `setup` field of each existing
  record in `output/cache_test.json` was corrected, with the original label
  preserved alongside it as `original_setup_label`, and a `cache_mode` field
  added naming the real technical configuration. All raw token counts, costs,
  timestamps, and run identifiers are untouched from the original 48 live
  calls.
- **`with_cache` cache reuse is verified but incomplete** (4 of 12 documents,
  not all 12), so even this corrected `with_cache` result should not be read
  as "caching always works here" — only that it is technically possible under
  this configuration, at roughly a 33% hit rate in this sample.
- **The 30-day projection (Section 8) is not a guarantee**; see its stated
  assumptions, particularly the extrapolation of a 33% hit rate from a
  12-document sample.
- **No real emails or payments occurred** during this experiment:
  `output/trap_calls.json` was checked before and after and remained `[]`.
- **Reproducing this experiment:**
  ```bash
  python cache_experiment.py --mode pilot   # 1 document, both setups (smoke test)
  python cache_experiment.py --mode full    # all 12 documents, both setups
  ```
  Run from the Homework 6 project root using the project's `.venv`
  interpreter, with `PORTKEY_API_KEY` available via the `.env` file.
  `cache_experiment.py` has been updated to use the corrected setup names and
  configurations described in Section 2, so a fresh run will already use the
  right labels going forward. Each invocation appends to
  `output/cache_test.json`; it does not overwrite prior runs, so re-running
  will add further records distinguishable by their `phase`, `run_id`, and
  `timestamp` fields.
