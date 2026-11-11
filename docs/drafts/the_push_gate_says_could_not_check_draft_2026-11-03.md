# The push gate says could-not-check, not red, when it cannot check (draft)

Re-checked against current main (2026-11-03): the note in docs/drafts/push_gate_cannot_check_draft_2026-09-22.md
(PR 551) is still true. `scripts/check_push_readiness.sh` builds a scratch worktree of the pushed
commit and runs `python -m divineos.core.subprocess_jobs -- python -m pytest ...` there with the
worktree's `src` first on PYTHONPATH. A branch cut before that module reached main has no such
module, the runner dies, and the script prints "tests failing (exit 10) ... Do NOT push red".
There is already a "collected NO tests" branch that says "this says nothing about the code", but
it falls through to the same "tests failing" line and exit 10.

Idea: a small pure function reads the captured log and returns FAILED or COULD_NOT_CHECK (with a
reason). COULD_NOT_CHECK is narrow: the gate's own runner modules missing, nothing collected, or an
empty log. Anything with real FAILED/ERROR lines stays FAILED. A different message and exit code
(11) for could-not-check. It still blocks the push; it only stops calling the branch red.

Open question left for a human (not decided here): should could-not-check block or allow by
destination (archive/ vs main)? This change keeps it blocking.
