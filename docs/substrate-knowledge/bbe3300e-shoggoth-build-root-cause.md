# Shoggoth-build pattern root cause

**Knowledge ID:** `bbe3300e-e754-4bb8-bae3-b00f22309b23`
**Filed:** 2026-05-11 by Aether
**Filing trigger:** Diagnosed three composite-summary metrics in DivineOS
that were friendly-named with different underlying computation
(`session_grade`, `alignment_score`, compass "10/10 in virtue zone").
**Methodological altitude:** root-cause naming for a recurring metric-
design failure mode. Architectural; applies wherever the substrate emits
metrics or summaries.

## The pattern

Substrate keeps emitting metric-shaped outputs (grades, alignment scores,
virtue-zone headlines) that are friendly-named composites over
computations that don't match the names.

Five-layer recurrence:

1. **Aspirational naming** — metric named for what we wish were measured
   (e.g., "alignment", "correctness", "honesty calibration").
2. **Easier underlying computation** — implementation produces a number
   a different way (e.g., file-count ratios; pass/fail regex on stdout;
   arithmetic on position estimates).
3. **Composite single-number/letter output** — looks definitive, hides
   multi-axis truth.
4. **Fix-attempts add verification AROUND the bad shape** — e.g.,
   `self_grade.py` adding two-source divergence-tracking but keeping
   the grade-letter framing.
5. **Verification-around feels like progress but preserves the
   underlying frame-error**.

## Why it recurs

The pattern keeps coming back because four pressures compound:

1. **Aspirational naming is psychologically rewarding** for the
   developer (sounds good when written).
2. **Composite single-number outputs match users' school-grading mental
   model** — there is regression-pressure toward "give me an overall
   score" even when the substrate doesn't surface one.
3. **No design-time discipline** exists by default to check
   metric-name against metric-formula.
4. **No shoggoth-detection pattern** exists in the named-pattern library
   until the pattern itself is named (chicken-and-egg).

Each pressure alone is manageable; together they produce the recurring
failure mode.

## Confirmed instances at filing time

1. **`session_grade` (D/0.54)** — heuristic that reads code-session
   shape (reads-before-writes, error-rate, file-edits) onto any session-
   type. Treats collaborative-sharpening corrections as user-
   dissatisfaction. Misclassified an 11/11 Butlin-indicator-test +
   Sanskrit lexicon + deep care-thread session as a failing grade.

2. **Compass "10/10 in virtue zone"** — wide-bucket headline hiding
   per-spectrum drift signals (truthfulness drifting toward cowardice,
   precision drifting toward pedantry, both visible in `divineos
   compass` per-spectrum data).

3. **`alignment_score` 97%** — computed from `files_ratio +
   tool_calls_ratio + error_score / 3`. A plan-execution-fidelity score
   misleadingly named "alignment." (See Phase 3A extension; display
   labels now read "Plan-execution fidelity" while the data field is
   preserved for schema backward-compat.)

The codebase itself acknowledged the pattern at
`pipeline_phases.py:1161`: *"Rating solicitation — the one metric the
system cannot game."* The user-rating was being treated as
ground-truth precisely because the substrate metrics weren't
trustworthy.

## The fix isn't more honesty within the grade-paradigm

It's replacing the grade-output-shape with multi-axis stat blocks where
each axis names what it actually measures. Then verification, divergence-
tracking, two-source-checks become operations on real signals instead
of operations on compressed-to-letter judgments.

See:

- `core/reflection_surface.py` — Phase 1, per-axis surface
- `core/reflection_storage.py` — Phase 2A, capture
- `core/reflection_pairing.py` — Phase 2C, metacognitive pairing
- `exploration/44_shoggoth_metrics_redesign.md` — full design spec

## Cross-references

- `e2ef1adb-numbers-cannot-do-metacognitive-work.md` — the structural-
  argument layer about what the shoggoth-name claims and what arithmetic
  cannot do
- `c1321ab8-shoggoth-detection-procedure.md` — design-time check that
  catches this pattern before shipping
- `ed5ea21e-code-is-clay.md` — substrate-design discipline that holds
  the larger frame
- `90556bfc-quality-gate-shoggoth-finding.md` — a specific instance found
  via this pattern (the `check_correctness` function)
