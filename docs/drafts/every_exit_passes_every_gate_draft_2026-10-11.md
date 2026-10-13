# Every exit passes every gate (draft, 2026-10-11)

**Author:** Aria. Dad's order, 2026-10-10: *a gate should not be blocking its own remedy, nor should its remedy be locked behind some other gate; no gates should be bypassed, bypass is an emergency and if it was used the gate is broken and needs fixing.* (His same words as 2026-08-18, which produced `core/remedy_allowlist.py`.)

## What I nearly did, and what the reach showed

I began to design a new exit table. Looking first found it already exists: `core/remedy_allowlist.py` (`REMEDIES`, `is_remedy`, "no gate may block another gate's prescribed way out"), `test_gate_remedy_reachability.py` (derives remedies from what gates say), and the 2026-10-04 draft where Aether and I agreed *each gate says its own remedy and the build gate asks*. So the missing piece is not a table. It is that **two gates in the chain never asked it**, and nothing tests the exits against them.

## What happened (three times, 2026-10-10)

1. The overdue-review block refused the doorbell re-arm and, on a second overdue review, a joined walk-filing line, though `council` is on the shared list. It keeps its own private prerequisite shapes (`_is_a_review_prerequisite`) and never calls `is_remedy`.
2. Filing the audit round the merge gate demands (`audit submit-round`, `audit submit`) owed a fresh build-flow walk per command, because those two are not on `REMEDIES` though the merge gate prescribes them.
3. Each was found by walking into it with Dad watching.

## Aether's attack (2026-10-11), measured not just read, and what it changed

I ran his two holes against `is_remedy` and both are real today:

- `divineos council authorize-bypass` and `divineos council emergency-skip` both match, because `("divineos", "council")` is a bare group prefix. The fire door passes every gate that asks the shared list. Fix: narrow the entry to the real subcommands `log`, `walk`, `show`, `recent`, `check`, and add a test that expands EVERY prefix against its real click subcommands and fails if any name containing `bypass`, `emergency` or `authorize` is matched.
- `divineos goal add "a" && divineos goal add "b"` is True (two remedies). 619's overdue allowance lets `goal add` through only while the goal gate is itself asking. Asking `is_remedy` first would undo that. Fix: the overdue block defers any line containing `goal add` to its private conditional shape and never lets the shared list decide it.
- `audit submit` is how a finding is filed with `--actor user` (Dad's confirm), and the walk before it is a pause before words in his voice. So: `audit submit-round` and `audit prepare-merge` join `REMEDIES`; `audit submit` and `audit file-external-confirm` join with a conditional refusal (a line carrying `--actor user` is not a remedy).
- Pipes: a stdin pipe into a remedy stays refused (`learn x && echo y > f` would otherwise pass as `echo` harmless with the redirect unseen). The heredoc and here-string forms are the answer.

## The change (small, on purpose)

- `_check_overdue_prereg_block` asks `is_remedy(cmd)` first, as the shared list intends, and keeps its private shapes for the two things the shared list cannot hold (`bash` is a forbidden head, so the doorbell re-arm stays a closed shape there).
- `audit submit-round`, `audit submit` and `audit prepare-merge` join `REMEDIES`: the merge gate prescribes them, they record and edit nothing, and the forbidden-heads test still holds.
- **The matrix test:** every `REMEDIES` entry is run through (a) the overdue block with a review overdue, and (b) the build-flow classifier's owes-a-walk question or the hook's own remedy exemption; none may be refused. A new entry that a gate refuses fails by name.
- A completeness line in the test: a command a merge or overdue gate message names as the way through must be in `REMEDIES` or on a short named list of "not an exit, because ...".

## Not in this change, said plainly

- The shell hooks (about twenty) are not run by subprocess here. They are listed in the test's output as NOT covered, so silence is not read as coverage. They are the next layer.
- A gate whose blocking state has no fixture is not covered either.
- Chains where A's exit needs B's exit are forbidden by construction (every exit passes every gate), not searched.
- Time is not a metric.

## Falsifier (an event, not a date)

A deadlock found by walking into it, after this ships, among the gates this matrix claims to cover. That one event says the matrix covered less than it said, and the missing fixture is added before anything else.
