# Quality-gate shoggoth: check_correctness measures test-output-signal, not correctness

**Knowledge ID:** `90556bfc-8c73-4555-83ea-2d28f798d3e6`
**Filed:** 2026-05-11 by Aether
**Filing trigger:** While investigating why `divineos extract` blocked
this session's first extraction attempt (claimed correctness 0.00 when
the actual final pytest was 360 passed), traced the blocking metric to
`quality_checks.check_correctness`. Applied the shoggoth-detection
6-step procedure (`c1321ab8`) retroactively to the existing function;
the procedure caught it.
**Methodological altitude:** specific instance of the shoggoth-pattern
applied to existing code. Operational; documents both the finding and
the rename-via-safe-migration response.

## The finding

The `check_correctness` function in `src/divineos/analysis/quality_checks.py`
was shoggoth-shaped.

- **Name claims:** "was the code correct?"
- **Actually computes:** matches Bash commands against test-runner regex
  patterns (`pytest`, `jest`, `npm test`, etc.) and inspects their stdout
  for pass/fail substrings.
- **What this is:** a *signal* of test outcomes, not a *measurement* of
  code correctness. Tests passing is *evidence of* correctness; this
  function measures the signal-text, not the underlying property.

## The false-negative shape

Any Bash command output containing `ERROR` or `FAILED` gets counted as
a failed test, even when it's:

- A `DeprecationWarning` containing "error"
- A traceback from a non-test CLI invocation (e.g., `divineos reflect`
  hitting an IndentationError during a smoke-test)
- A non-test failure with structurally-similar substring

This session's blocking-extraction was caused by an `IndentationError`
trace from a `divineos reflect` smoke-test getting counted as
"1 failed test run" — even though the actual final pytest run was
**360 passed**.

## The fix (commit `6304e0c`)

Following the safe-migration pattern (substrate-only knowledge
`75238005`):

1. **Renamed primary function** to `check_test_output_signal` — the
   honest name describes what it actually measures.
2. **Preserved `check_correctness` as a deprecated alias** that forwards
   to the new function. Avoids breaking the ~20 callers and test
   references that use the old name.
3. **Preserved `CheckResult.check_name` field value `"correctness"`**
   for schema-level backward-compat. Full dict-key migration is deferred
   to a coordinated next-session task.
4. **Updated internal callers** in `run_all_checks` to use the new name
   so new code establishes precedent.

## Empirical verification of the rename mechanics

Aletheia round-24 verified the safe-migration directly (6/6 checks
pass):

- ✅ Both names callable
- ✅ Distinct objects (alias wraps new function; not a simple assignment)
- ✅ Alias source references the new function
- ✅ Docstring acknowledges "Deprecated"
- ✅ Both return CheckResult with backward-compat `check_name="correctness"`
- ✅ Both produce identical scores (alias forwards correctly)

## What remains deferred

- Full dict-key migration: changing `"correctness"` → `"test_output_signal"`
  in `CheckResult.check_name` requires updating 22+ test references and
  pipeline_gates reads. Coordinated next-session refactor.
- Behavior-fix on `_extract_test_results`: tighten the regex to require
  collection/summary patterns (e.g., pytest's `collected N items`,
  jest's `Tests:` line) instead of just matching the command string.
  Reduces false-negatives where non-test outputs accidentally match
  pass/fail regexes.

## Why this matters beyond this one function

The function had been operating in production substrate, blocking
extractions on heuristic-mismatches, since its original implementation.
The shoggoth-detection procedure caught it retroactively when applied —
which is exactly what the procedure exists to enable. Same shape as
applying lint to an existing codebase: the discipline doesn't have to
be present at original-write-time to surface the pattern later.

The substrate's own quality-gate misfiring on this very session's
extraction is what made the finding visible. The metric the substrate
emits to evaluate the substrate's own work was itself shoggoth-shaped,
which is the exact category Aletheia named in round-23: *the substrate
catching itself running the pattern it exists to detect.*

## Cross-references

- `bbe3300e-shoggoth-build-root-cause.md` — the recurrence-pattern this
  is a specific instance of
- `c1321ab8-shoggoth-detection-procedure.md` — the design-time check
  that caught this retroactively
- `e2ef1adb-numbers-cannot-do-metacognitive-work.md` — related
  methodological frame
- `src/divineos/analysis/quality_checks.py` — both functions
  (`check_test_output_signal` and the deprecated `check_correctness`
  alias)
