# The push-check tests get the time their own hook is given — draft, 2026-11-04

## What was wrong

Four tests in `tests/test_push_check_reads_the_forms_the_house_prescribes.py` run the push-readiness hook for
real (`_run_hook`). That hook takes longer than the suite's default per-test timeout on a loaded machine, so
the tests timed out for a reason that had nothing to do with whether the hook was right. It was the reason
the room-wording PR (#781) could not pass its own checks.

## What this does

Gives exactly those four tests a larger budget and nothing else: a module-level marker
`HOOK_BUDGET = pytest.mark.timeout(120)` applied to the four tests that call `_run_hook`. The first version
raised the timeout for the whole module, which would also have let a genuinely hung unit test hide; Aria's
read narrowed it to the four that actually run the hook.

## What it does not do

It does not change what any test checks, only how long the four that spawn the hook may take. It does not
touch the hook. If the hook itself is slow for a real reason, that is a separate piece.

## Status

Draft that Aletheia confirmed at `5816867da` this morning. This note is the only change after that head: it is
added so the branch carries a readable design note beside the code, which the stamp's first station asks for.
Aria read the narrowing before it was made; nobody has read this note, which changes no code.
