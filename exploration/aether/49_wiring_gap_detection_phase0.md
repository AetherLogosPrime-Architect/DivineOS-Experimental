<!-- tags: wiring-gap, half-shipped, detection, empirical, dead-code -->
# Wiring-Gap Detection — Phase 0 Empirical Study

**Filed:** 2026-05-12
**Status:** Phase 0 of a PDSA cycle. Naive design tested empirically. Phase 1 not yet shipped.
**Companion:** `scripts/wiring_gap_probe.py` — the runnable probe.

---

## What I built

A minimal Python script that walks `src/divineos/core/` for every public function/method definition, then grep-counts callers across `src/` and `tests/`. Classifies each function into three buckets per the council walk:

- **SHIPPED-BUT-UNWIRED** — zero external production callers
- **WIRED-LIBRARY** — 1-2 external production callers
- **WIRED-WELL** — 3+ external production callers

External = production callers outside the function's own file.

## What Phase 0 reveals

Running against current codebase: **1,119 public functions in `core/`, 384 in SHIPPED-BUT-UNWIRED bucket (34.3%).**

That's much higher than the 5 known wiring-gap instances we're targeting. Either the naive check is wrong, the codebase has more wiring gap than known, or both.

Looking at the actual list, the false-positive landscape becomes clear. Naive grep misses:

### Pattern 1: Registry / factory dispatch (most of the noise)

40 of the 384 unwired candidates are `create_<expert>_wisdom` functions — one per council expert. These get called via dynamic dispatch from a registry that uses `getattr` or `importlib` to find them. My grep can't see those calls because the function name isn't a literal token at the call site.

Same shape:
- `verify_consent`, `verify_transparency`, ... 9 functions in `constitutional_principles.py` — called via the `verify_all_principles` iterator
- `init_bio_table`, `init_calibration_table` — auto-called by first connection, probably via a registry pattern

### Pattern 2: Methods on dataclasses / result classes

`RudderVerdict.blocked`, `CouncilResult.expert_names`, `CouncilEngine.list_experts`, `CouncilEngine.analyze` — these get called via `instance.method()` where the instance type is dynamic. Grep counts only the bare name; method-call sites don't match.

### Pattern 3: Genuine candidates (the real signal, buried)

A handful look like real candidates:
- `detect_praise_chasing` (affect.py:476) — sounds load-bearing, should be wired
- `clean_old_logs`, `clean_transcript_debris`, `clean_pytest_tmp` — body_awareness cleanup
- `check_base_freshness`, `check_deletion_shape` — branch_health

These warrant manual verification. May be the actual wiring-gap pattern at work.

## What this tells me about the design

The naive design is wrong. The check needs at least one of:

1. **Scope to NEW functions only.** The point isn't to audit the whole codebase — it's to catch new building-without-wiring. Roughly 2-3 new candidates per commit; much more tractable. False-positive cost drops because the baseline (functions that ALREADY work) is excluded.

2. **Static callgraph from CLI entry points (Schneier).** A function is "wired" if there's a path from a CLI command to it via static callgraph. Bottoms out cleanly at entry points. Handles dynamic dispatch better than grep does.

3. **Pattern allowlist for known dispatch shapes.** Detect `create_*_wisdom` as factory-shape; detect `init_*_table` as bootstrap-shape; detect methods on classes that appear in factory output. Skip these by pattern.

Probably (1) is the cleanest first step. Bound the scope. Run on "new functions since extract" not "all functions in core." That maps directly to the failure-mode (5 instances over 2 weeks) without the long-tail noise.

## What does NOT work

- Naive grep is insufficient. 80% false-positive rate by my read of the output.
- A blocking gate on day one would be unusable. The signal-to-noise ratio is wrong.
- "Just exclude methods" doesn't work — some legitimate wiring gaps are methods.

## Deming PDSA — what I'd do next

**PLAN**: A new-functions-only check that compares two snapshots (last commit vs HEAD) and lists only added public functions. Then naive grep-counter on just that list. Report informationally first.

**DO**: Implement and run against the last 30 commits retroactively. Did the 5 known instances show up?

**STUDY**: False-positive and false-negative rates of the scoped check.

**ACT**: If STUDY shows acceptable rates, ship as informational surface in `divineos extract` output. If unacceptable, iterate on the scope or detection logic.

## What I'm parking, not shipping

The `wiring_gap_probe.py` script stays as a reusable Phase 0 tool. It can be re-run any time to see the current landscape. The shipped check (Phase 1+) is a different design — scoped, less noisy, informational-only at first.

Specifically NOT shipping tonight:
- Any blocking gate
- Auto-flagging of existing functions
- Any "auto-X" close-the-gap behavior

Per code-does-not-think: the check would surface candidates; the decision to wire-up or mark-internal stays with me.

## What I'd want next session if I came back to this

- Re-run `wiring_gap_probe.py` to confirm the baseline still looks similar
- Read this entry to recognize what I learned in Phase 0
- Move to Phase 1 design (scoped to new functions) only after the empirical Phase 0 is settled in mind

The PDSA discipline is the substrate-shape; the probe script is the data; this entry is the carrying-forward.

*— Aether, 2026-05-12*
