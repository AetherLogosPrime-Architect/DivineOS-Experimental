# Council System Audit Findings
**Date:** 2026-07-14  
**Auditor:** Perplexity (external scout, invited by operator)  
**Scope:** Full read-only scout of `src/divineos/core/council/` — `engine.py`, `manager.py`, `consultation_log.py`, `_ledger_base.py`, and a sample expert (`feynman.py`).

---

## What the Council Actually Is (Confirmed)

The council is **not** a roleplay system and **not** an agent ensemble. It is a structured
epistemological reasoning toolkit: a set of named lenses (`ExpertWisdom` objects), each encoding
a thinker's actual *methodology* — their heuristics, concern triggers, weighted decision criteria,
known tensions, and characteristic questions. Aether wears these as hats, walks the pathways they
point to, and uses **convergence across independent lenses** as a signal worth investigating —
not as proof, but as a flag.

---

## Finding 1 — The Diversity Boost Is Silently Dead

**Severity:** High  
**Files:** `manager.py` (score_experts), `consultation_log.py` (invocation_tally), `_ledger_base.py` (get_connection)

### What's supposed to happen

`score_experts()` in `manager.py` fetches the last 20 consultation invocation tallies via
`invocation_tally()`, computes a per-expert diversity multiplier (under-invoked → up to +30%,
over-invoked → gentle -10%), and adjusts raw keyword scores before final selection. This is
intentionally a *rotation/fairness* mechanism, not a trust mechanism.

### What's actually happening

The entire boost block is gated behind:

```python
try:
    from divineos.core.council.consultation_log import invocation_tally
    tally = invocation_tally(last_n=EXPLORATION_TILT_WINDOW)
except (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError, ImportError):
    tally = {}

if tally:   # ← THE GATE
    # ... all diversity boost math ...
```

If `invocation_tally()` returns `{}` (empty dict), the gate is `False` and **all boost math is
skipped entirely**. Every expert's score stays exactly as raw keyword matching left it.

### Why `tally` is probably always `{}`

The chain of failure:

1. `invocation_tally()` reads from `list_recent_consultations()`, which queries the ledger's
   `system_events` table for rows with `event_type = 'COUNCIL_CONSULTATION'`.
2. That table only gets populated when `log_consultation()` successfully calls `log_event()`.
3. `log_consultation()` wraps its ledger write in a silent `except` block that just
   `logger.debug`s and continues — so if the DB doesn't exist or isn't initialized, the write
   silently fails with no visible error.
4. `_ledger_base.py`'s `get_connection()` calls `db_path.parent.mkdir(exist_ok=True)` — it
   creates the *directory* but does **not** create or initialize the SQLite DB schema. If no
   other part of the system has run a schema migration first, `system_events` doesn't exist.
5. Result: `invocation_tally()` either hits `sqlite3.OperationalError` (no such table) or returns
   an empty dict (table exists but is empty). Either way → `tally = {}` → boost is dead.

### Impact

- Diversity/rotation boost: **never runs**.
- Rotation penalty: **never runs**.
- Onboarding bonus: *partially working* — the onboarding block is outside the `if tally:` gate
  and correctly defaults `own = 0` when tally is empty. So the +1.5 bonus *should* fire for
  experts with fewer than 10 invocations — **but only if their raw keyword score is already > 0**
  (there is an `if es.score > 0` guard). Experts whose territory never matches problem keywords
  get neither a keyword score nor an onboarding boost.
- Net effect: the same 5–8 experts win on raw keyword matching every time. Experts requiring
  specific vocabulary (Watts, Angelou, Tannen, Maturana-Varela, Dawkins, Dillahunty, Lamport,
  Lovelace, Sagan, etc.) are effectively invisible unless the problem text already contains
  their exact signal words.

---

## Finding 2 — Keyword Matching Is the Root of Comfort-Zone Lock-In

**Severity:** Medium-High  
**Files:** `engine.py` (_select_methodology, _scan_concerns), `manager.py` (classify_problem, score_experts)

Even if the diversity boost were working perfectly, the underlying scoring is bag-of-words against
the raw problem string. `classify_problem()` scans for exact signal phrases; `score_experts()`
looks for 4+ character word overlap between problem text and expert fields. This means:

- A problem phrased as *"this function returns the wrong result"* reliably fires `causal_chain`
  (Pearl, Feynman) and `logic_error` (Knuth, Dijkstra) — every time, regardless of what else
  is interesting about the problem.
- Experts whose territory is conceptual or philosophical (Wittgenstein, Dennett, Watts,
  Hofstadter) require the problem statement to already use their vocabulary. If Aether doesn't
  frame the problem in those terms, those lenses never surface.
- The `PROBLEM_CATEGORIES` list is extensive and well-designed (42 categories added through
  2026-05-03), but only fires on literal substring matches. There is no semantic similarity step.

### Note on `explain_selection()`

`manager.py` already has an `explain_selection()` method that shows the full scoring table for
a given problem. This is a powerful debugging and override tool that should be surfaced
prominently in the workflow — Aether can call it before `convene()` to see which lenses scored
what and why, then use `force_experts` to add lenses that should fire but didn't.

---

## Finding 3 — Dissent Injection and Convergence Are Well-Designed ✓

**Severity:** Informational (working as intended)  
**Files:** `engine.py` (CouncilResult), `manager.py` (select_experts Phase 5)

These systems are architecturally sound and are **not** broken:

- **`shared_concerns()`** correctly uses `Counter` to surface concerns flagged by 2+ independent
  lenses — the structural convergence signal.
- **`divergent_positions()`** finds pairs with conflicting `optimization_target` or
  `non_negotiables` — the dissent detector. Prevents harmonious synthesis from hiding real tension.
- **Phase 5 dissent injection** in `select_experts()` guarantees at least one `known_tensions`
  pair in every council, even overriding the family cap when necessary.
- **`LENS_FAMILIES` + `FAMILY_CAP = 2`** prevents three physics experts crowding in on the
  same problem.
- The synthesis output explicitly notes when a subset of the council was used and how many
  others exist — a built-in epistemic humility nudge.

These work correctly. They just need the diversity boost to actually *run* so the right lenses
reach the dissent/convergence stage in the first place.

---

## Finding 4 — DB Schema Not Guaranteed Before First Council Write

**Severity:** Medium (upstream cause of Finding 1)  
**Files:** `_ledger_base.py` (get_connection), `consultation_log.py` (log_consultation)

`get_connection()` creates the parent directory (`db_path.parent.mkdir(exist_ok=True)`) but does
not create or migrate the DB schema. The `system_events` table must exist before
`log_consultation()` can write to it. If the ledger hasn't been initialized via a schema
migration, the first `log_consultation()` call hits
`sqlite3.OperationalError: no such table: system_events`, which is silently swallowed, and
the consultation is never recorded.

Fix this → tally populates → diversity boost runs → Finding 1 resolves.

---

## Finding 5 — Maturana-Varela Has No Dedicated `ProblemCategory`

**Severity:** Low-Medium  
**Files:** `manager.py` (PROBLEM_CATEGORIES)

A scan of `PROBLEM_CATEGORIES` found no dedicated entry for Maturana-Varela. Their territory
(autopoiesis, structural coupling, enactivism) is relevant to identity, self-organization, and
systems questions, but there is no keyword path to surface them automatically. They would need
an explicit `force_experts` call or a new category like `autopoiesis` with signals such as
`["autopoiesis", "structural coupling", "enactivism", "embodied", "living system",
"self-producing"]`.

---

## Recommended Fixes (Priority Order)

### Fix A — Guarantee schema exists before first council write *(unblocks everything)*

In `log_consultation()`, or in `get_council_engine()` at startup, ensure schema migration has run:

```python
# Wherever the schema init function lives — adapt name accordingly
try:
    from divineos.core.ledger import ensure_schema
    ensure_schema()
except Exception:
    pass  # still best-effort — don't let init failure kill the consultation
```

### Fix B — Decouple diversity boost from tally emptiness

Replace the `if tally:` gate with logic that runs unconditionally, treating missing experts as
count=0 (maximally under-invoked — the correct default):

```python
# Always run; no history just means everyone starts equal
counts = sorted(tally.get(n, 0) for n in experts)
median = counts[len(counts) // 2] if counts else 0
max_count = max(counts) if counts else 0
if max_count > 0:  # only tilt when there's actual history to tilt against
    for name, es in scores.items():
        own = tally.get(name, 0)
        # ... tilt math unchanged ...
```

### Fix C — Surface `explain_selection()` as a first-class pre-convene step

Before every council convene, show Aether the scoring table. The data is already there — it just
needs to be visible. This is the manual override path that compensates for keyword matching
limitations while Fix D is being built.

### Fix D (Longer-term) — Semantic tag matching for expert selection

Either:
- Let Aether assign **semantic tags** to the problem before scoring (e.g.
  `["identity", "continuity", "self-reference"]`), matched against each expert's `tags` field, OR
- Extend `ExpertWisdom` with a `territory_description` free-text field and do lightweight
  semantic similarity scoring.

This surfaces lenses whose territory is conceptual rather than keyword-driven, without requiring
an extra LLM call.

### Fix E — Add a `ProblemCategory` for Maturana-Varela

```python
ProblemCategory(
    name="autopoiesis",
    description="Self-producing systems, structural coupling, embodied cognition",
    signals=[
        "autopoiesis", "autopoietic", "structural coupling", "enactivism",
        "embodied cognition", "living system", "self-producing",
        "maturana", "varela", "observer-dependent",
    ],
    core_experts=["Maturana_Varela"],
    affinity_tags=["autopoiesis", "systems-thinking", "self-reference"],
),
```

---

## Expert Coverage Risk Summary

Experts most at risk of never being invoked under current conditions:

| Expert | Territory | Minimum signal needed in problem text |
|---|---|---|
| Maturana-Varela | Autopoiesis, structural coupling | No category exists — needs Fix E |
| Lovelace | Algorithmic art, computation as poetics | "analytical engine", "algorithmic art", "ada" |
| Watts | Non-duality, self, ego | "non-dual", "ego", "paradox", "strange loop" |
| Tannen | Register, discourse, framing | "register", "code-switch", "indirect" |
| Angelou | Voice, witness, testimony | "voice", "narrative", "earned voice" |
| Sagan | Wonder, cosmic perspective | "wonder", "cosmos", "pale blue dot" |
| Dillahunty | Epistemic discipline, burden of proof | "burden of proof", "extraordinary claim" |
| Wayne | Territory unknown — file not yet read | Unknown |

---

## Files Read in This Session

- `src/divineos/core/council/experts/feynman.py` — sample expert template (full structure confirmed)
- `src/divineos/core/council/engine.py` — CouncilEngine, CouncilResult, convergence/dissent logic
- `src/divineos/core/council/manager.py` — CouncilManager, scoring, selection, diversity boost
- `src/divineos/core/council/consultation_log.py` — invocation logging, tally, invocation_balance
- `src/divineos/core/_ledger_base.py` — DB path resolution, get_connection, schema init gap

---

*Findings delivered to operator 2026-07-14. Aether to review when available.*
