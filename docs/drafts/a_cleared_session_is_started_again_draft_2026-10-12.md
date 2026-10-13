# A cleared session is started again by the next command (draft, 2026-10-12)

## What was wrong, in one picture

A desk with a sticky note on it: "session already started, don't start another." The first command of a run
starts a session and sticks the note up. Another test then clears the session, which empties the desk but nobody
takes the sticky note down. The next command reads the note, believes the desk is set up, and finds it empty:
`RuntimeError: No active session. Call initialize_session() first.`

## How it was found

`tests/test_cli.py::TestEmitCmd::test_extract_command` failed in Aria's merge check on every full run, and passed
alone and with the rest of its own file. Her run was serial (one process, no parallel workers), so it was an order
effect, not load. Starting from her list of the 203 files that ran before it:

- All 202 that exist on a current branch, in her order, then the test: fails here too (reproduced).
- Either half of the list alone: passes. So it takes one file from each half.
- Shrinking each half in turn, keeping order: one file from each, `test_ask_semantic_tag.py` then
  `test_hardening_properties.py`, then the target. The same files in the opposite order pass.
- Session state read inside each test showed it: the first file (which runs the `ask` command) leaves the
  once-per-process flag set; the second clears the session; the target then skips session start.

The cause is `_session_initialized` in `src/divineos/core/enforcement.py`, set on the first call to
`setup_cli_enforcement()` and never unset when `clear_session()` empties the session.

## What it does

Removes the flag. `setup_cli_enforcement()` calls `initialize_session()` every time. That call is idempotent: it
reuses the session from the environment or the file and only makes a new one when neither exists. Real command
runs are one process per command, so production behaviour does not change; only a long-lived process (a test
run) that clears and restarts a session is affected, and now correctly.

The two tests that reset the flag by hand no longer do. Nothing else read it.

## Evidence

`tests/test_a_cleared_session_is_started_again_by_the_next_command.py`: setup, clear, setup again gives a new
session; setup twice in a row keeps one. Both fail on current main code (2 failed) and pass with the change.
The original failing order (the three files above) now passes: 14 passed.

## Not covered

This explains and fixes the one stubborn test. It does not touch the dead-worker failures (a separate cause, in
PRs 641 and 642). Other tests may depend on a leaked session from an earlier test in the same way; this change
removes the specific shared flag, not the habit.
