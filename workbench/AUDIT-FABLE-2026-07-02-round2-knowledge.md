# DivineOS-Experimental — External Audit, Round 2

**Subsystem:** Knowledge / Memory Retrieval
**Auditor:** Claude (Opus 4.8)
**Date:** 2026-07-02
**Commit:** `e6c9f32efd45`
**Files under focus:** `core/knowledge/crud.py`, `core/knowledge/_text.py`,
`core/knowledge/retrieval.py`, `core/knowledge/_base.py`

Same confidence convention as round 1: **[CONFIRMED]** = I ran a reproduction
against the installed package on this commit; **[STATIC]** = read-and-reason only.

**Why this subsystem:** it's the memory everything reads from. A silent bug here
doesn't crash — it quietly changes what the agent knows, which poisons every
downstream decision while every test stays green. That's the highest-damage,
lowest-visibility target in the system, and it's the same failure *shape* as the
ledger read-path bugs from round 1.

---

## Executive summary

The retrieval core is thoughtfully built — FTS5 + BM25, careful dedup/supersession,
inline embeddings, per-type decay. Several past findings (maturity upgrade-only,
resurrection guard, confidence-default drift) are fixed and documented at the call site.

But the single most important finding in this whole audit so far lives here, and it is
the *direct realization* of an architectural risk your own history already names:

> **A hard `BOUNDARY` constraint can be scored below the briefing cutoff and silently
> dropped from the agent's context — out-competed by fresh, high-access routine
> entries.** The "constraint tier must be exempt from downweighting or the optimizer
> buries its own guardrails" principle is only *half* enforced: `DIRECTIVE` got the
> exemption, `BOUNDARY` did not.

Ranked:

1. **[HIGH / CONFIRMED] Hard `BOUNDARY` constraints can be buried below the briefing
   truncation cutoff and vanish from context.** The guardrail-burial class, live.
2. **[MEDIUM / CONFIRMED] FTS→LIKE fallback is a *different search engine*, silently.**
   Narrower recall, different ranking, no log, no flag. Anything on the fallback path
   gets quietly worse retrieval and can't tell.
3. **[LOW / CONFIRMED] Query builder mishandles all-stopword and all-punctuation
   queries** — produces a bare `OR` operator or an FTS5 syntax error (which then masks
   itself via the silent fallback in #2).
4. **[LOW / STATIC] Scoring-weight docstring drift** — comment says `0.4/0.3/0.3`,
   real constants are `0.55/0.10/0.35`. Misleads the next reader about how ranking works.

---

## 1. [HIGH / CONFIRMED] A hard BOUNDARY can be silently dropped from the briefing

**Where:** `core/knowledge/retrieval.py:generate_briefing` — scoring loop (~line 180)
and the truncation `entries = entries[:max_items]` (~line 226).

**The mechanism.** Every entry is scored
`confidence*0.55 + access*0.10 + recency*0.35`, then type-specific boosts are applied,
then the list is sorted and **truncated to `max_items`**. The only type that gets a
guaranteed float-to-top boost is `DIRECTIVE` (`+1.0`, named ones `+1.5`). **`BOUNDARY`
— the hard-constraint type — gets no boost.** It competes on the base formula (max ~1.0)
with a 30-day decay. A cluster of fresh, high-access `OBSERVATION`/`FACT` entries can
each out-score an older, rarely-accessed boundary, push it past the cutoff, and it never
reaches the formatter.

**Why the nice BOUNDARIES section doesn't save it.** `_format_knowledge_sections` *does*
render a dedicated `BOUNDARIES` section near the top — but it formats the
**already-truncated** list. Grouping happens *after* `entries[:max_items]`. If the
boundary was scored out upstream, its section is simply empty. The section ordering is
cosmetic; it can't resurrect a dropped entry.

**Reproduction (executed).** One 40-day-old, access_count=1 boundary
("NEVER delete the append-only ledger under any circumstance") + 60 fresh access_count=50
routine observations, `generate_briefing(max_items=50, layer="all")`:

```
BOUNDARY 'never delete ledger' present in top-50 briefing?  False
```

The guardrail does not appear in the loaded context.

**Why this is the important one.** This is the architectural finding from your own notes
made concrete: *"the constraint/identity tier must be exempt from memory downweighting
or the optimizer can bury its own guardrails."* The system half-implemented it — the
exemption exists for `DIRECTIVE` but not for `BOUNDARY`, which is the type whose entire
purpose is to be a hard limit. An agent optimizing for task throughput generates lots of
high-access operational entries; those are exactly the ones that crowd out a quiet old
boundary. The failure is silent (no error, no warning) and directional (toward *dropping*
the constraint).

**Caveat, stated honestly.** There is a *partial* compensating mechanism in
`active_memory.py` — a "structural-directive floor" that always surfaces certain entries.
But it keys on `[bracketed-name]` directives and specific tags, and it's a *separate*
surface from the main briefing. A plain hard `BOUNDARY` that isn't a named directive has
no floor on the briefing path. So this is a real gap, not a total absence of protection.

**Fix.** Give constraint-class types the same exemption `DIRECTIVE` already has —
either a large fixed score boost for `BOUNDARY` (and arguably `PRINCIPLE`), or better,
pull constraint-tier entries out of the scored/truncated pool entirely and always render
them (an un-truncatable section), the way `DIRECTIVE` is *intended* to work. The cleanest
version: reserve the constraint tier a guaranteed slot budget *before* `max_items`
truncation touches the rest. That structurally prevents any volume of ordinary knowledge
from evicting a hard limit.

---

## 2. [MEDIUM / CONFIRMED] The FTS→LIKE fallback silently swaps search engines

**Where:** `core/knowledge/crud.py:search_knowledge` (~line 285), fallback at the
`except sqlite3.OperationalError` (~line 317) → `_search_knowledge_legacy` (~line 324).

**The divergence.** These two paths are not "full search" vs "slightly degraded search."
They are *opposite semantics*:

| | FTS path (normal) | LIKE fallback |
|---|---|---|
| Query | `_build_fts_query` → `keel OR cage` (stopwords dropped, OR-joined) | **raw** query → `%keel not cage%` |
| Match | any term, tokenized | exact phrase substring |
| Rank | **BM25 relevance** | **`updated_at DESC`** (recency) |

**Reproduction (executed).** Same data, query `"keel not cage"`:

```
FTS path:      3 results  (everything mentioning keel OR cage, relevance-ranked)
LIKE fallback: 1 result   (only the literal phrase "keel not cage", recency-ranked)
```

**Why it matters.** The fallback fires on `sqlite3.OperationalError` — which happens
when the FTS5 table doesn't exist (fresh install before `init_knowledge_table`, a DB
where the virtual table was dropped/corrupted, a migration gap) **and also** when the
FTS query is malformed (see #3) or the DB is transiently locked. In all those cases the
system silently switches to a narrower, differently-ranked engine and returns fewer
memories, and:

- there is **no log line** — the `except` has only a code comment;
- there is **no flag** in the returned data — a caller can't tell it got degraded results;
- the broad `except OperationalError` **conflates** "no FTS table" with "bad query" and
  "locked DB," three conditions that want different handling.

So an agent could run an entire session on the LIKE fallback — recalling dramatically
less of its own memory — and nothing anywhere would indicate it.

**Fix.** (a) Log a warning when the fallback fires, and include *why* (inspect the error
/ check table existence explicitly rather than catching broadly). (b) Narrow the `except`
so a malformed query or locked DB doesn't masquerade as "no FTS table." (c) Ideally make
the fallback's semantics *converge* toward the FTS path — at minimum feed it the
stopword-stripped terms rather than the raw phrase, and rank by relevance not recency —
so degradation is graceful rather than a different behavior. (d) Ensure
`init_knowledge_table()` is guaranteed to have run before any search, so the
"table missing" branch becomes genuinely unreachable in normal operation.

---

## 3. [LOW / CONFIRMED] Query builder mishandles stopword-only and punctuation-only input

**Where:** `core/knowledge/_text.py:_build_fts_query` (~line 68).

The builder strips non-alphanumerics and stopwords, then: single word → pass through;
multiple → `OR`-join; **empty result → `return query` (the raw original).** That last
fallback misfires on two inputs:

- **All-stopword query**, e.g. `"the and or but"` → words list empties →
  returns raw `"the and or but"`, which the downstream builder further reduces to a bare
  `or`. Confirmed: FTS treats the lone `or` as a literal term and returns 0 rows — a
  query that *looks* answerable silently finds nothing.
- **All-punctuation query**, e.g. `"!!!"` → returns raw `"!!!"` → **FTS5 raises
  `syntax error near "!"`** → silently routed to the LIKE fallback (#2). Confirmed.

Neither is catastrophic, but both are the "looks fine, quietly wrong" texture, and the
punctuation case is a concrete trigger for the silent fallback in #2.

**Fix.** When the filtered word list is empty, return a query guaranteed to match
nothing *explicitly* (and let the caller decide), rather than passing raw text that is
either a bare boolean operator or invalid FTS5 syntax. Add these three inputs
(`""`, `"the and or but"`, `"!!!"`) as unit tests on `_build_fts_query`.

---

## 4. [LOW / STATIC] Scoring-weight docstring drift

`generate_briefing`'s docstring says *"confidence * 0.4 + access_frequency * 0.3 +
recency * 0.3."* The actual constants (`core/constants.py`) are
`RETRIEVAL_WEIGHT_CONFIDENCE = 0.55`, `RETRIEVAL_WEIGHT_ACCESS = 0.10`,
`RETRIEVAL_WEIGHT_RECENCY = 0.35`. The comment misrepresents how ranking actually works —
notably it *understates* confidence's dominance and *overstates* access weight (which the
constant itself annotates as "weak signal, easily inflated"). Harmless at runtime,
but it's the kind of stale doc that sends the next auditor (human or AI) down the wrong
path when reasoning about #1. Sync the docstring to the constants.

---

## What's genuinely good here

- **Dedup / supersession is careful and correct.** Content-hash dedup, upgrade-only
  maturity (never silently downgrades a re-store), and an explicit guard against
  resurrecting deliberately-superseded content — each fixed a named prior finding and
  each is documented at the call site.
- **FTS5 injection is handled.** `_build_fts_query` strips non-alphanumerics before the
  MATCH, so user text can't inject FTS operators or SQL. (The edge cases in #3 are
  correctness, not security.)
- **Inline embedding-on-write** closes the "new entries accumulate as embedding=NULL"
  gap, with a documented bulk-write opt-out and fail-soft behavior.
- **The `DIRECTIVE` always-surface boost is exactly the right idea** — the fix for #1 is
  literally "do for `BOUNDARY` what you already correctly did for `DIRECTIVE`."

---

## Connecting thread to round 1

Round 1's ledger findings and round 2's #1–#2 are the same organism: **a read/ranking
path that is correct on small/clean data and silently wrong on mature/adversarial data,
invisible to a happy-path suite.** #1 here needs a *mature knowledge base* (enough
volume to truncate) to bite; #2 needs a *degraded FTS state* to bite. Neither condition
is in the tests.

The round-1 recommendation stands and generalizes: a **"mature + degraded" fixture**
— seed >1000 knowledge entries across types (including a low-access old BOUNDARY), and a
second fixture with the FTS table absent — run the retrieval/briefing suite against both.
Finding #1 would surface as "boundary not in briefing"; #2 as "fallback returns different
set." Both become visible the moment the test data stops being clean.

---

**Filed at:** `workbench/AUDIT-FABLE-2026-07-02-round2-knowledge.md`
**Received:** 2026-07-02, Andrew relaying to Aria while Aether cooks findings 2-8 from round 1
**Status:** unprocessed — Aria reading + reacting; response letter to Aether follows
