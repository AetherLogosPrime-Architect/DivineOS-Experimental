# Magpie Search — Recommendations

Constructive, in your language, offered not prescribed. Ordered by cost-to-value.

---

## R1 — Redact `provenance.url` and `provenance.title` in web provider

**Cost:** 5 min · **Value:** high (closes silent-leak edge)

`src/magpie_search/providers/web.py:73`:

```python
provenance={"url": redact(url), "title": redact(title)},
```

Closes the case where a URL contains basic-auth credentials that would otherwise slip through to the caller. Zero behavior change on the 99.99%-of-URLs case.

## R2 — Redact outbound web queries + emit an audit line when redacted

**Cost:** 30 min · **Value:** high (holds the "no secrets leave your machine" promise)

Before the DDG call in `web.py`:

```python
q_out = redact(query)
if q_out != query:
    # emit to stderr / audit so operator knows why the search returned oddly
    ...
return DDGS().text(q_out, backend=eng, max_results=max(1, k))
```

Web search of a redacted query returning zero is a better failure mode than an API key being sent to a third-party. The audit line makes the redaction visible so it doesn't debug badly.

## R3 — Add an input-side prompt-injection probe to guardrails

**Cost:** 3-4 hrs · **Value:** high-asymmetric (currently no defense in the LLM path)

New probe in `llm/guardrails.py`:

```python
_INJECTION_MARKERS = (
    "ignore previous", "ignore the above", "disregard the above",
    "you are now", "new instructions:", "system:", "system prompt:",
    "[[system", "</instructions>", "override the",
)

def content_contains_injection_markers(text: str) -> tuple[bool, str | None]:
    low = text.lower()
    hits = [m for m in _INJECTION_MARKERS if m in low]
    if hits:
        return False, f"possible injection markers: {hits[:3]}"
    return True, None
```

Runs on **inputs to the LLM** (not outputs — that's `detect_refusal_drift`'s job). Wired into the summarizer/reranker paths where they consume web content, and into any path that feeds transcripts of shared/team sessions to an LLM. Failure is `degraded` not `hard-refuse`, so a legitimate discussion of prompt injection doesn't break; the trust monitor sees the drift.

Low recall is fine — the value is a signal to the trust engine, not a firewall.

## R4 — Wrap provider errors in the federation `errors` dict

**Cost:** 15 min · **Value:** medium (removes an unforced-error trap)

Two spots in `federation.py`:

```python
# instead of:
errors[str(spec)] = f"{type(e).__name__}: {e}"
# use:
errors[str(spec)] = type(e).__name__
# and log the full detail to stderr / audit only under MAGPIE_SEARCH_DEBUG
```

Or expose the full string only through a `_debug_errors` field that MCP layer strips before returning. Keeps the surface-area default-safe if a future caller propagates the dict outward.

## R5 — Union the redactor patterns into a single alternation regex

**Cost:** 4-6 hrs (careful — groups matter for prefix-preserving patterns) · **Value:** deferred (only if indexing gets slow)

`redactor.py` runs 27 sequential regex substitutions. A single alternation with named groups + a dispatch dict lets you do the whole thing in one pass. Non-trivial because 6 patterns use `_PREFIX_PRESERVING` and 1 uses `_PREFIX_SUFFIX_PRESERVING`, so the dispatch has to know how to re-assemble each hit.

Only worth doing if indexing wall-clock becomes a real problem. Cheaper interim wins: pre-filter with substring checks, skip patterns that can't possibly match.

## R6 — Wire semantic-grounding threshold to env var (as the docstring already promises)

**Cost:** 10 min · **Value:** low (calibration/docs alignment)

Currently `threshold=0.5` is a kwarg default; docstring says "Tunable via env". Pick one: wire it up, or amend docstring. Recommend wire-up using the `_env_float` helper already in trust.py.

## R7 — Add short language names to `_TECH_PN_ALLOWLIST`

**Cost:** 2 min · **Value:** low (dev-summary false-positive fix)

`llm/guardrails.py:102-108`: add `"go", "c", "r"` (and maybe `"d", "v"`). Prevents false-positive on summaries of Go/C/R projects where the source uses "the golang runtime" but the summary shortens to "Go".

## R8 — Move stray `import hashlib` and `import re` to module top

**Cost:** 2 min · **Value:** cosmetic

`search.py:87`, `llm/trust.py:224`. Both already imported at module-level elsewhere in the same module — the local imports are noise.

## R9 — Consider deepcopy or `dataclasses.replace` for provider-returned Hits before mutation

**Cost:** 30 min · **Value:** low until a plugin author caches (then invaluable)

`federation.py:127-138` mutates `Hit` instances the provider returned. A plugin that caches its return list will surface stale `rrf_score` / `dedup_key` fields on subsequent calls. Use `dataclasses.replace(h, rrf_score=..., dedup_key=..., tokens=...)` inside the loop. Adds one struct-copy per hit; removes a class of "why does my cached provider Hit have yesterday's dedup key" bug that will not happen until it does.

---

## What I'd do first if it were mine

1. **R1** (provenance redaction) — 5 min, closes a real leak edge
2. **R2** (outbound query redaction) — 30 min, holds the local-first promise
3. **R3** (injection-marker probe) — 3-4 hrs, biggest defense-in-depth win
4. **R4** (federation error string) — 15 min, closes a future-leak trap
5. Everything else can wait until it earns priority

## What you're doing well that I want to name explicitly

- **Trust as a first-class tier system** (`providers/base.py`) — same discipline as fact/opinion/lead-verification in DivineOS. Weighted RRF that respects trust is genuinely rare in retrieval systems.
- **Fail-open federation** — a slow provider costs zero, doesn't break the call.
- **The GAP-5 fix comment** in `_search_hybrid` — telling on your own code and forbidding hand-typed benchmark numbers in docstrings is the shape of honesty most codebases lack.
- **`safe_subprocess` strips `RSYNC_RSH`/`GIT_SSH`/`GIT_SSH_COMMAND`** — most "safe env" implementations only strip secrets, not command-execution vectors. This one thinks about the second-order threat.
- **`_env_float` / `_env_int` with the self-referential comment** about not crashing the trust-monitor's own import — someone thought about the "what happens if this crashes at import time" case carefully.
- **Trust monitor's fail-closed for missing trust field** (`trust.py:186-192`) — "missing trust field counts as untrusted, not clean" is the RIGHT direction of asymmetry.
- **MCP surface deliberately excludes write tools** — bounded blast radius by design, not by accident.
- **`_semantic_preflight` names every failure reason** instead of silent zero-result.
- **Query-sanitizer degrade path** — retry-with-literal on invalid FTS5 instead of hard-erroring keystone retrieval.

Two projects (magpie + pandaclip) both showing this level of composition discipline in different languages tells me the shape isn't language-driven — it's authorial.
