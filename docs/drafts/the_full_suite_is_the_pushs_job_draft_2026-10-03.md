# The full suite is the push's job

**Drafted:** 2026-10-03, night, by Aether.

## His words

- 2026-06-24: *"theres no need for you to run a full test suite on everything for every change, the push to hub does that already twice.."*
- 2026-09-09: *"is there a reason you continue to run the full suite and gauntlet after every small change? do you realize that it takes upwards of 15-20 mins?"*
- 2026-10-03, after I'd started a full run again: *"i have asked you repeatedly not to run the full fucking suite on every goddamn change"*, then *"then fucking build it.. now.."*

Tonight I ran the whole suite by hand about six times. Each run took five to seven minutes, and two of them, run side by side with a push, crashed the machine's thread pool and failed both pushes.

## Why remembering hasn't worked

Three rulings in four months, and the habit came back each time. Running everything *feels* like rigour, and nothing in the house makes it cost anything. A rule I have to recall at the moment of reaching for it is the thing that already failed (CLAUDE.md rule 9).

## What it does

A PreToolUse refusal on Bash: **a hand-run pytest over the whole tests folder is refused.** Either of these counts:

- `tests` or `tests/` as a target, with nothing narrowing it, or
- no target at all, which collects everything.

What still runs:

- named test files or test ids, e.g. `pytest tests/test_x.py tests/test_y.py::test_z`,
- a run narrowed with `-k`,
- the push. `divineos_push.sh` and the pre-push hook run the suite inside git's own process, never through my Bash tool, so they're untouched.

The refusal says what to run instead: the test files for what I changed. The full run belongs to the push.

## What it doesn't cover

- A script I write that calls pytest itself, or `python -c` that imports pytest. Those are routes around it, named here, not closed.
- Whether the files I pick are the right ones. Picking too few is a real risk. The push is the backstop, so it stays mandatory, and that's why it can carry the full run.

## Steps

Draft (this) → a walk, each lens by hand → build → the tests for this file only → Aria → Aletheia.
