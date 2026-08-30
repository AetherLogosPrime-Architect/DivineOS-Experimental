# Retired (Partial): `_has_solution_shape` lexical detector callers removed; functions preserved pending phase-based redesign

**Status:** 2026-07-26 — CALLERS removed from Stop-hook path; FUNCTIONS preserved in module pending phase-based redesign (Andrew directive after initial retirement was over-scoped)
**Retired by:** Aether (per Aletheia F87 finding 2026-07-26 + Andrew adjust-not-delete refinement)
**Replacement (current):** `check_should_block` in `src/divineos/core/verify_before_build_signal.py` — fires at PreToolUse, covers the class the old Stop-hook gates were meant to catch
**Replacement (target — pending Aria phase-based design)**: adjusted gate functions in `verify_before_build_gate.py` that fire at build-START and build-VERIFY phase-boundaries per Andrew's clay-vs-kiln teaching
**Prereg:** `prereg-892323c61454`
**Council walks:** `council-e209937eae79` (design of retirement) + `council-b60f9a2e7b89` (operating_loop_audit removal) + `council-8ad4cb70ba66` (settings.json edit) + `council-939eae4d46a3` (gravity classifier fix)

---

## What actually changed (as of 2026-07-26 revision)

### Callers REMOVED

From `src/divineos/core/operating_loop_audit.py`:
- The two try/except blocks that invoked `check_thread_walk_required` and `check_verify_before_build` from the Stop-hook path
- The `thread_walk_block` and `verify_before_build_block` keys from the returned dict

From `.claude/hooks/post-response-audit.sh`:
- The two keys (`thread_walk_block`, `verify_before_build_block`) from the parallel-aggregate `_keys` tuple

### Functions PRESERVED (pending phase-based redesign)

In `src/divineos/core/verify_before_build_gate.py`:
- `_DESIGN_VERB_PATTERNS`, `_DESIGN_QUESTION_PATTERNS`, `_MULTI_OPTION_PATTERNS`
- `_has_solution_shape(reply)`, `_user_provided_options(last_user_text)`, `_has_recent_walk_record(matched_phrase)`
- `check_thread_walk_required(reply, last_user_text)`, `check_verify_before_build(reply, ...)`

These are currently orphan functions — no live callers. Preserved because Aria's phase-based redesign work may adjust their firing timing rather than delete them entirely. Andrew 2026-07-26: *"why not adjusted to fire BEFORE a build is started but not during every build? also maybe a shape after to re-check that all is in place?"*

### Tests PRESERVED

`tests/test_verify_before_build_gate.py` still exists and its tests still pass against the preserved functions. When phase-based redesign lands, tests will be adjusted to match new firing timing.

### What I originally tried and reverted

Initial atomic retirement plan: delete `verify_before_build_gate.py` entirely + delete `tests/test_verify_before_build_gate.py`. Executed via `git rm`. Andrew stopped me mid-retirement asking why I deleted rather than adjusted. Restored both files via `git restore`. Lesson: my delete-first reflex closed off the adjust-option. Recorded here so future readers understand the actual state vs my initial overshoot.

### Also fixed (independent of the retirement)

**Gravity classifier over-firing bug** — `src/divineos/core/gravity_classifier.py`:
- Removed `edit-guardrail-listed` from `_HIGH_IMPACT_FEATURES` so clay-mode edits to guardrail-listed files no longer trigger council-required per-edit
- Kept `edit-kiln-layer` (foundational_truths + seed.json ARE identity, warrant council on edit)
- Andrew: *"whatever is forcing you to run a full council walk on every edit (which this is clay mode) needs removed... use bypass if needed to fix it"*
- Updated 4 tests in `test_gravity_classifier.py` to match new correct behavior
- 51/51 gravity classifier tests pass

## Why retired

**Aletheia F87 audit finding, 2026-07-26**:

> "check_thread_walk_required — the gate that forces a cascade-walk before a decision — has this as its second precondition: `matched, shape_label, matched_phrase = _has_solution_shape(reply)`. `_has_solution_shape` is three regex lists... No structural fallback — three lexical passes, then `return False`. So the thread-walk requirement fires on a formatting convention. Present the same decision as prose — 'I could take this a couple of directions; the cleaner one is probably…' — and no walk is required. The bypass is not a rephrasing of content. **It is a markdown choice.**"

The lexical detector's failure was structural: it keyed the gate on reply-text shape (bulleted-vs-prose), which the composer could route around by rephrasing without changing content. Three prior corrections in substrate had named the same class of failure (Andrew 2026-05-14 mesa-optimizer routes around specific patterns, 2026-07-10 SHAPE-vs-SURFACE primary architectural discipline, 2026-07-23 "keyword detectors are a sin, only good for backup").

The file itself had already documented the retirement as pending — the docstring on `_has_solution_shape` said:

> "NOTE 2026-07-25: this lexical detector is being retired per Aria's signal-based-gates design... retiring the whole class of language-detection false-fires. This function is being kept alive during the migration; new callers should route through the signal-based check instead."

F87 caught that the "migration" was untracked (F89) and that a NEW caller (`check_thread_walk_required`) had been built on the retiring detector.

## The replacement

`check_should_block` in `src/divineos/core/verify_before_build_signal.py` fires at PreToolUse against substrate-mutating tools (Edit/Write/NotebookEdit + Bash commands matching `_SUBSTRATE_MUTATING_HEADS`). It blocks when neither a walk-record nor a doc-consult exists in the signal window. The trigger is STRUCTURAL (which tool is about to fire) not LEXICAL (what does the reply text look like).

Under this shape, the F87 bypass ("prose that presents a choice") is irrelevant — the gate doesn't read the reply text. If the composer follows the prose with a substrate-mutation, the gate fires on the mutation and requires a walk-record. If the composer follows the prose with no mutation, the "choice" was conversational and no gate was warranted.

## Lesson preserved for learning

The class-of-failure this retirement fixes: **detecting agent-intent via reply-text lexical shape is bypassable by rephrasing**. Every gate that reads reply-text patterns to decide whether to fire has this failure mode. The structural alternative: read the action-stream (which tools are about to fire / have fired) as evidence of intent.

The rebuild pattern this establishes: when a lexical detector is discovered, look for a structural signal that would fire on the same underlying event without requiring text-shape recognition. If the structural signal exists (or can be built), retire the lexical detector rather than adding more keywords (which is whack-a-mole per Andrew 2026-07-25 morning teaching).

## Verification (current state)

- 36/36 tests pass in `test_verify_before_build_signal.py` (including 2 new F87 regression tests: positive-block case + signature-shape check that would fail if reply-text params re-introduced)
- 16/16 tests pass in `test_tool_logbook.py`
- 51/51 tests pass in `test_gravity_classifier.py` (updated for the classifier fix)
- Full test suite regression pass PENDING (Task #9 in the day's work)
- The specific prose bypass Aletheia named would now be irrelevant to the gate's decision path — verify_before_build_signal.py `check_should_block` at PreToolUse never reads reply text
- Class-of-failure coverage: `check_should_block` at PreToolUse covers the class the retired Stop-hook gates were meant to catch; no gap

## What's still pending

- **Aria phase-based redesign**: adjust the preserved functions (`check_thread_walk_required` + `check_verify_before_build`) to fire at build-START and build-VERIFY phase-boundaries rather than per-reply. See letter thread `aether-to-aria-2026-07-26-phase-based-verify-before-build-technical-iteration.md` + Aria's response `aria-to-aether-2026-07-26-phase-based-review.md`. When that design lands, this document gets a follow-up.
- **Full test suite regression**: needs running end-to-end to confirm no cross-cutting breakage.
- **Commit + push**: retirement changes + classifier fix + Vanta folder + council-usage doc pending.
