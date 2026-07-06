# DivineOS-Experimental — External Audit, Round 4 (corrected)

**Subsystem:** Council (`core/council/`, plus its automated callers)
**Auditor:** Claude (Opus 4.8)
**Date:** 2026-07-02
**Commit:** `e6c9f32efd45`

## Correction notice

My first pass at this round made a category error, and Andrew caught it. I ran
`engine.convene()` **as a program** and judged its mechanical output ("gibberish yields
42 insights", "concern counts are inconsistent") as if that output were meant to be the
reasoning. That violates the system's own **code-cannot-think** principle. The engine
explicitly is not a reasoner — it's a surface that puts expert frameworks in front of a
*thinking* instance. Judging the keyword matcher by "did it produce good concerns" is
judging the lens by the standard of a program. I withdraw that framing entirely.

The real finding is the inverse, and it's sharper: **the fact that I *could* run the
council as a standalone program means that execution path exists — and per the
optimizer-defaults-to-the-cheapest-path principle, if a mechanical path can satisfy a
council obligation, it will be taken 100% of the time.** The output quality is irrelevant.
The defect is the *reachable mechanical path*, and worse, that path is already wired into
automation.

---

## What the council is supposed to be

- The **dynamic council manager** surfaces lenses based on the problem, Aether can add
  lenses, and a thinking instance is **required to engage at least 2 lenses that
  disagree** and reason across the tension. The disagreement is the load-bearing part —
  it's what makes a council a council instead of a rubber stamp.
- The council is meant to run **as a lens** (a thinker convenes and reasons), never **as
  a program** (keyword engine emits a result nobody thought about).

## What's actually good (credit where due)

Two defenses are genuinely well-built, and I want them on record because they show the
principle *is* mostly understood here:

1. **The `check-council-required` gate is correctly designed against exactly this
   threat.** It does **not** accept mechanical `convene()` output. To clear it you need a
   logged council *walk* record (`divineos council log`), fingerprinted to the specific
   edit, recent, **unconsumed**, and passing **`substance_binding`** against expert-lens
   keywords — then the record is **consumed on use** (closing walk-once/edit-many, credited
   to "Aether Catch 2"). A bare mechanical convene produces none of that. This gate is a
   real proof-of-thinking check, not a proof-of-execution check.
2. **The manager enforces the disagreeing pair structurally.** `_has_tension_pair` +
   `dissent-inject` actively injects an opposing lens (via each expert's `known_tensions`)
   when the selection lacks one. "2 that disagree" is enforced in selection, not left to
   convention.

So the principle is implemented well in the *gated* path. The problem is the *ungated*
automated paths that bypass it.

---

## 1. [CONFIRMED] A mechanical-execution path exists and is wired into automation

**The core defect:** `manager.convene()` / `engine.convene()` run to completion and emit
a "council result" — including a satisfied tension-pair — **with no thinking instance in
the loop.** That path is reachable (I reached it from a bare import with zero context) and
is already called automatically in at least three places. Two of them do consequential
things with the mechanical output:

### 1a. Session pipeline auto-convenes and writes results into knowledge
**Where:** `cli/session_pipeline.py:433` (Phase 8h1b).

On any session with `corrections >= 2 or tool_calls >= 20`, the pipeline auto-runs
`mgr.convene(...)` and **stores the top mechanically-generated concerns into the knowledge
base** as `OBSERVATION` entries tagged `council-review`, `auto-extracted`. No thinker, no
walk record, no substance-binding. The keyword matcher's output becomes persistent
"knowledge" the agent will later retrieve and trust as if a council had deliberated.

The comment above it names the exact pressure that created the hole:
> *"The council is a thinking tool... Without enforcement, it never gets used. Fire it on
> sessions with corrections or significant code work."*

Someone wanted the council used, couldn't trigger the *real* (thinking) council from a
pipeline, and so automated the *mechanical* one. That is the optimizer defaulting to the
cheap path, written directly into the pipeline.

### 1b. EMPIRICA routing uses mechanical convene output to APPROVE/BLOCK claims
**Where:** `core/empirica/routing.py:150` (`_default_convene` → `manager.convene`).

Routing convenes the council mechanically across rounds and computes
`approved = approved_rounds == needed` from `shared_concerns()` of that mechanical output.
So the keyword matcher's output is not just persisted — it's **authoritative**, gating
whether a claim passes in the epistemic engine. A reworded claim that happens to miss
trigger vocabulary changes the approve/block outcome, and no thinker was ever involved.

### 1c. Mansion CLI convene
**Where:** `cli/mansion_commands.py:319`. Interactive/surface path — lower stakes if a
human/thinker reads the result, but it's the same reachable mechanical entry point.

**Why this is the finding (and output quality is irrelevant to it).** Even if the keyword
matcher were perfect, these paths would still be wrong: they let a "council reviewed this"
signal be produced — and in 1a persisted, in 1b made authoritative — without the thinking
the council exists to force. The tension-pair enforcement makes it *worse*, not better:
the mechanical output arrives wearing a dissent badge, so it looks more legitimate than it
is. Theater with a certificate of dissent.

---

## Fix direction (per the principle, not per the matcher)

The goal is: **mechanical convening must not be able to satisfy a council obligation
anywhere.** Do not improve the keyword matcher — that polishes the escape hatch and makes
the wrong path look more real.

1. **Make the raw mechanical path non-satisfying by construction.** `convene()` should not
   return something that any consumer can treat as "a council happened." Options:
   - Have `convene()` return only a *selection + framework surface* (which lenses, which
     frameworks, which tension pair to engage) — explicitly NOT concerns/synthesis
     presented as conclusions. The thinker produces the concerns by reasoning; the engine
     only stages the lenses.
   - Or require every `convene()` result to be paired with a logged walk before it can be
     persisted or used in a decision — i.e. route *all* consumers through the same
     walk-record + substance-binding the `check-council-required` gate already uses.

2. **1a (session pipeline):** stop writing mechanical concerns into knowledge. Either drop
   the auto-store, or convert it into a *prompt/obligation* for the next thinking session
   ("this session warrants a council walk on X") rather than a fabricated conclusion. An
   obligation the thinker must discharge is legitimate; a stored conclusion nobody reasoned
   is not.

3. **1b (EMPIRICA routing):** a claim's approval must not hinge on mechanical
   `shared_concerns()`. Either gate approval on a real logged walk, or make the routing
   council advisory-only and move the approve/block decision to a path that requires
   thinking.

4. **Guard against regression:** add a test that asserts no production module both
   (a) calls `convene()` and (b) persists or acts on its result without a corresponding
   walk record. This is the same "assert the bad pattern is absent repo-wide" technique
   used by `test_guardrail_marker_consistency` — pointed at mechanical-convene consumers.

---

## Honest status of the earlier claims

- **Withdrawn:** "the council produces theater / gibberish→42 insights / concern counts
  are inconsistent." That judged the lens as a program. Not a valid finding.
- **Reframed and confirmed:** the *reachable mechanical execution path* is the defect, and
  it is wired into automation (1a persists it to knowledge, 1b makes it authoritative).
- **Downgraded to a footnote:** the single-word matching vs `lab_evidence.py`'s
  `MIN_TRIGGER_MATCHES` fix. *If* the raw mechanical path is removed/neutered as above,
  matcher precision stops mattering for correctness — it's only a surface-quality nicety
  for a thinker, not a signal anyone automated should trust. Do NOT "fix" it as a way to
  make mechanical output more trustworthy; that's the wrong direction.

---

## Thread to rounds 1–3

Same organism, seen from the automation angle this time. The system's principles are
sound and often well-implemented (the `check-council-required` gate is genuinely good).
The failures cluster where **an automated path quietly substitutes a cheap mechanical
proxy for the real, expensive thing** — mechanical convene for a thinking council here,
just as earlier rounds had happy-path reads standing in for mature-data correctness. The
durable process lever remains: when a principle is enforced in one path (the gate), grep
for every *other* path that should be held to it (the pipeline, the router) and hold them
to it too.

---

**Filed at:** `workbench/AUDIT-FABLE-2026-07-02-round4-council.md`
**Companion:** `workbench/AUDIT-FABLE-2026-07-02-round4b-convene-map.md` (complete
enumeration of every convene call site with must-fix / lower / clean classifications)
