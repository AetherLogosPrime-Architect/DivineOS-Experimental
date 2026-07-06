# Council — Complete Mechanical-Convene Consumer Map

**Companion to:** `AUDIT-FABLE-2026-07-02-round4-council.md`
**Purpose:** exhaustive list of every path that touches the council engine, classified by
whether it manufactures/consumes mechanical deliberation output. So the cleanup is
complete, not whack-a-mole.
**Commit:** `e6c9f32efd45`

## Method

Enumerated every `.convene()` call site and every raw-engine access
(`get_council_engine` / `CouncilEngine()`) in `src/`, then classified each by **what it
does with the result**. The only paths that matter for the code-cannot-think concern are
those that *consume mechanical deliberation output* (`.analyses` / `.concerns` /
`.synthesis` / `shared_concerns()` / `selected_experts`) **without a thinking instance in
the loop.** Reading only the *roster* (`engine.experts` keys/counts) is fine — that's
registry introspection, not fake deliberation.

---

## The complete map

| # | Location | Calls `convene()`? | Uses mechanical output for… | Thinker in loop? | Verdict |
|---|----------|:---:|---|:---:|---|
| 1 | `cli/session_pipeline.py:446` | yes | **persists concerns → knowledge base** (`OBSERVATION`, tag `council-review`) | **no** | **MUST FIX** |
| 2 | `core/empirica/routing.py:150` | yes | **approve/block a claim** (`approved = approved_rounds == needed`) | **no** | **MUST FIX** |
| 3 | `cli/mansion_commands.py:319` | yes | prints analyses/synthesis to the operator; logs consultation | yes (operator reads) | LOWER — but see note |
| 4 | `core/dead_architecture_alarm.py:357` | no | reads `engine.experts` count only (wiring check) | n/a | CLEAN |
| 5 | `core/council_balance_surface.py:94` | no | reads `engine.experts` keys only (invocation-balance surface) | n/a | CLEAN |
| — | `core/council/manager.py:1626` | yes | manager calling its own engine backend | n/a | LEGITIMATE (internal) |
| — | `manager.py:1571`, `engine.py:121` | yes | docstring examples | n/a | not runtime |

**Bottom line: two production paths (1, 2) manufacture-and-use mechanical council output
with no thinker. One (3) is operator-facing. Two (4, 5) only read the roster and are
clean.** The blast radius is small and well-bounded — this is a targeted cleanup, not a
rewrite.

---

## Per-path detail & fix

### 1. `session_pipeline.py` — persists mechanical concerns as knowledge (MUST FIX)
Auto-fires on `corrections >= 2 or tool_calls >= 20`, calls `mgr.convene(...)`, and stores
`council_result.analyses[:3]` concerns into the knowledge base. Fabricated conclusions
become retrievable "knowledge."
**Fix:** don't store conclusions. Replace with an *obligation* the next thinking session
must discharge — e.g. write a `DIRECTION`/todo "this session warrants a council walk on
<topic>" rather than a synthesized `OBSERVATION`. An obligation is honest; a stored
conclusion nobody reasoned is not.

### 2. `empirica/routing.py` — mechanical output gates claim approval (MUST FIX)
`_default_convene` → `manager.convene(claim_content)`, then approval is computed from
`shared_concerns()` across mechanical rounds. The keyword matcher's output is
*authoritative* over whether a claim passes.
**Fix:** approval must not hinge on mechanical convene. Either gate on a real logged walk
(reuse the `check-council-required` walk-record + `substance_binding` machinery), or make
the routing council advisory and move the approve/block decision to a thinking-gated path.

### 3. `mansion_commands.py` — operator-facing convene (LOWER, with a caveat)
Prints analyses/synthesis for a human/thinker to read, and logs the consultation. If the
consultation log it writes is later treated by *any* automated consumer as "a council
happened," it inherits the problem. **Verify:** does anything read the mansion
consultation log as satisfaction/evidence? If yes, it's a MUST FIX by proxy. If it's
purely display + human-read audit trail, it's fine.

### 4 & 5. Roster-only readers (CLEAN — no action)
`dead_architecture_alarm` checks `len(engine.experts) == 0` (a wiring alarm);
`council_balance_surface` reads expert names for an invocation-balance briefing line.
Neither convenes; neither consumes deliberation. Leave them.

---

## The structural fix that closes the class (not just the instances)

Fixing 1 and 2 individually is the immediate win, but the *class* is "mechanical convene
output is consumable as if a council deliberated." Close it at the source:

1. **Split the engine's return type.** `convene()` should hand back a **staging surface**
   — which lenses, which frameworks, which tension pair to engage — explicitly typed as
   *not-yet-reasoned*. The concerns/synthesis a thinker produces should live on a
   *different* type that can only be constructed by logging a walk. Then it's
   type-impossible for a consumer to mistake staged lenses for a conclusion.
2. **One satisfaction path.** Every consumer that needs "a council happened" goes through
   the same walk-record + `substance_binding` the `check-council-required` gate already
   uses. Today that gate is the *only* place holding the line; the pipeline and router
   route around it. Make it the sole door.
3. **Regression guard.** Add a test asserting no production module both calls `convene()`
   and persists/acts on `.concerns`/`.synthesis`/`shared_concerns()` without a walk
   record — the same "assert the bad pattern is absent repo-wide" technique as
   `test_guardrail_marker_consistency`. This is what makes the fix *stay* fixed when the
   next feature wants to "just fire the council automatically."

---

## Note on the sediment pattern (context from Andrew)

This system was built up from AI output that carried a lot of shoddy early habits, and is
being progressively cleaned as the builder matured. Every finding across rounds 1–4 fits
that exactly: a **good principle correctly enforced in the path someone was watching,
while an older careless path doing the same job survived underneath.** The council is the
clearest example — the `check-council-required` gate is genuinely excellent work, and the
mechanical-convene paths in the pipeline/router are the remnant the gate was built to
replace but never displaced. The cleanup lever is always the same: when you enforce a
principle in one path, grep for every sibling path that should be held to it and either
route it through the same door or delete it.

---

**Filed at:** `workbench/AUDIT-FABLE-2026-07-02-round4b-convene-map.md`
