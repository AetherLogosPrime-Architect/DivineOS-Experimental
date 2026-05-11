# Shoggoth-detection procedure (design-time discipline)

**Knowledge ID:** `c1321ab8-f024-4591-8cd1-f3fbcb366bed`
**Filed:** 2026-05-11 by Aether
**Filing trigger:** Phase 3B of the shoggoth-metrics redesign. After
diagnosing the recurrence-pattern in `bbe3300e`, the discipline needed
an explicit design-time check the agent (or any contributor) can apply
to candidate metrics before shipping.
**Methodological altitude:** design-time discipline. Operational
checklist; applies whenever a new metric, score, grade, alignment-
number, summary-letter, or composite-output is added to the user-facing
surface.

## The 6-step procedure

Before shipping any new metric, score, grade, alignment-number, summary-
letter, or composite-output to the user-facing surface, walk this
checklist:

### 1. Write the metric NAME

Plain English. Don't gesture; commit to what you'd call this in the
user interface.

### 2. Write what the metric is supposed to MEASURE in plain language

The cognitive operation or substrate property the name claims to track.

### 3. Write the actual COMPUTATION the code performs in plain language

Step by step. What inputs, what arithmetic or aggregation, what output.

### 4. Compare (2) and (3) word-by-word

If they don't match, the metric is **shoggoth-shaped and must not ship**.
Either rename the metric to describe what the code actually does, or
change the code to compute what the name claims.

### 5. Goodhart-resistance check

How could this metric score well WITHOUT being true to what it claims
to measure? Name the failure modes.

If you can't articulate that, the metric isn't ready — you haven't
thought through what it can be gamed against.

### 6. Composite check

Does this need to be a single number/letter, or would a multi-axis stat
block be more honest?

Single-number outputs hide multi-axis truth. Prefer multi-axis unless
compression genuinely serves clarity (and you can name what bits the
compression discards).

## How to invoke

`divineos ask "shoggoth"` surfaces this entry along with related substrate-
knowledge. Apply at design-time, not at debug-time.

## Why design-time matters

The pattern recurs because aspirational naming is psychologically
rewarding for the developer (sounds good when written) AND users
habituated to school-grading expect single-number outputs. The shoggoth-
shape gets built when these pressures aren't resisted at design-time.

If the check happens after shipping, the metric is already producing
visible numbers that downstream consumers depend on, and the fix becomes
a coordinated migration instead of a not-shipping decision.

## Test cases (instances this procedure caught or would have caught)

- ✅ **`alignment_score`** — name claims "alignment"; computation is
  `(files_ratio + tool_calls_ratio + error_score) / 3`. Names don't
  match. Caught by step 4.

- ✅ **`session_grade`** — name claims session quality; computation is
  a code-session-shape heuristic that misfires on philosophical sessions.
  Names partially match but step 5 reveals the metric can score well
  by satisfying the heuristic without the session being good.

- ✅ **Compass "10/10 in virtue zone"** — name claims virtue alignment;
  computation is "number of spectrums whose position is anywhere in the
  broad center bucket." Step 4 reveals the wide-bucket compression
  hides actual drift signals.

- ✅ **Phase-2C numerical `divergence`** — name claims "honesty
  calibration"; computation is `agent_estimate - substrate_position`.
  Step 4 reveals arithmetic on two floats cannot do metacognitive work
  (see `e2ef1adb-numbers-cannot-do-metacognitive-work.md`).

- ✅ **`check_correctness`** — name claims "was the code correct?";
  computation is regex on Bash stdout for pass/fail substrings. Names
  don't match. Renamed to `check_test_output_signal` (see
  `90556bfc-quality-gate-shoggoth-finding.md`).

## Cross-references

- `bbe3300e-shoggoth-build-root-cause.md` — the recurrence-pattern this
  procedure exists to interrupt
- `e2ef1adb-numbers-cannot-do-metacognitive-work.md` — structural-argument
  layer for step 4 when the metric is named for cognitive work
- `90556bfc-quality-gate-shoggoth-finding.md` — a specific instance
  this procedure caught retroactively
- `ed5ea21e-code-is-clay.md` — the substrate-design frame this
  procedure operates inside
