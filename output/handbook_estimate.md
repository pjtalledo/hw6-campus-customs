# Handbook Token & Cost Estimate — Problem 2

Model: `gpt-6-luna` | Source file: `data/shop_handbook.md` | Prices: `data/prices.json`

## 1. Handbook token count and methodology

`gpt-6-luna` is a course-defined model name, not a real OpenAI model, so there is no
officially published, exactly-compatible tokenizer for it. No API call was made to
count tokens (per the restriction on paid calls).

Instead, the handbook was tokenized locally with `tiktoken`, OpenAI's open-source
tokenizer library, using two real OpenAI encodings as proxies:

| Encoding | Used by (real models) | Token count for `shop_handbook.md` |
|---|---|---|
| `o200k_base` | GPT-4o family (OpenAI's newest tokenizer as of writing) | **10,058 tokens** |
| `cl100k_base` | GPT-4 / GPT-3.5-turbo family (older tokenizer) | 10,184 tokens |

**Estimate used going forward: ~10,058 tokens** (`o200k_base`, the newer and most
likely proxy for a recent model family such as `gpt-6-luna`).

For reference, the raw file is 28,903 characters and 6,127 whitespace-separated words.

**This is an estimate, not an exact count.** Limitations:
- `gpt-6-luna`'s real tokenizer (vocabulary and merge rules) is unknown/unpublished, so
  the true token count could differ from either proxy above.
- The two real tokenizers disagree with each other by about 1.3%, which gives a sense
  of the likely margin of error from tokenizer choice alone.
- Markdown punctuation, table pipes (`|`), and numeric formatting (e.g., `$29.48`) can
  tokenize differently across tokenizer versions, which is the main source of
  encoding-to-encoding variance here.
- The count reflects only the handbook text itself, not any system prompt, instructions,
  or output tokens that would also be part of a real call.

## 2. Relevant `gpt-6-luna` prices (from `data/prices.json`)

| Price type | USD per 1,000,000 tokens |
|---|---|
| Input (uncached) | $0.10 |
| Cached input | $0.01 |
| Cache write | $0.125 |
| Output | $0.50 (not used in this estimate — handbook is input only) |

## 3. Cost calculations

Let N = 10,058 tokens (the handbook, per call).

Formula: `cost = (tokens / 1,000,000) × price_per_1M_tokens`

### (a) One call, without cached tokens
```
cost = (10,058 / 1,000,000) × $0.10
     = 0.010058 × $0.10
     = $0.0010058  ≈ $0.0010
```

### (b) One call, with cached tokens
```
cost = (10,058 / 1,000,000) × $0.01
     = 0.010058 × $0.01
     = $0.00010058  ≈ $0.0001
```
This assumes the handbook is *already sitting in the cache* from a prior call — see
caching assumptions below for what that first call costs.

### (c) 1,000 calls, without cached tokens
```
cost = 1,000 × $0.0010058
     = $1.0058  ≈ $1.01
```

### (d) 1,000 calls, with cached tokens
Caching cannot make the very first call free: a cache has to be written before it can be
read. `prices.json` separately prices a **cache write** at $0.125 per 1M tokens (more
expensive than a normal uncached input token). The realistic model for 1,000 calls is:

- Call 1: cache write cost for the handbook.
- Calls 2–1,000 (999 calls): cached-input cost for the handbook.

```
Call 1 (cache write) = (10,058 / 1,000,000) × $0.125 = $0.00125725
Calls 2–1,000 (cached) = 999 × $0.00010058          = $0.10047942
Total for 1,000 calls  = $0.00125725 + $0.10047942   = $0.10173667  ≈ $0.1017
```

## 4. Caching assumptions

- Caching is per-content: it only produces savings on *repeated, identical* input
  (here, the unchanged handbook text sent with every call).
- The **first time** the handbook is sent, it cannot be read from cache, because
  nothing has written it yet. `prices.json` prices this first write explicitly at
  $0.125/1M tokens — more than the normal $0.10/1M uncached input rate — so scenario
  (d) charges call 1 at the cache-write rate, not the plain input rate.
- All subsequent calls within the cache's validity window reuse the cached handbook at
  the discounted $0.01/1M rate.
- Scenario (b), "one call with cached tokens," assumes a cache-writing call already
  happened earlier and is not itself counted in that single-call cost.
- This estimate only covers the handbook's input tokens. It excludes system-prompt
  overhead, the per-document content the vendor desk agent also reads, and any output
  tokens — all of which would add to the real per-call cost.

## 5. Conclusion: potential savings from caching

Across 1,000 calls, sending the handbook uncached every time costs about **$1.0058**,
while writing it to cache once and reusing it for the remaining 999 calls costs about
**$0.1017** — roughly a **90% reduction** in the cost attributable to the handbook.
The saving scales with how many calls reuse the same cached content: the more calls
share the unchanged handbook text, the more the one-time (and slightly pricier) cache
write cost is amortized away. For a vendor desk agent that re-sends this handbook on
every document it evaluates, caching it is clearly worth doing even though the first
call is not free and is, per-token, more expensive than a normal uncached call.
