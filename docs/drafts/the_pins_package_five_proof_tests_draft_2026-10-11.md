# The pins package: five proof-tests in one request (draft, 2026-10-11)

**Author:** Aether, carrying the cloud helper's work. Aletheia, 2026-10-11 ("one line each"): #605, #607, #609, #610 are *proven, and land through the pins package. Open it as a PR with the five proven files (these four plus #602's) and I'll sign it by number. Then close these as superseded.*

## What this is

Five test files from the helper's reproduction branches, carried unchanged except where noted, so one request can be read and signed instead of five. None touches code: each test pins a defect the house has by marking its failing test `xfail(strict=True)`, so it passes quietly now, goes red the day someone fixes the defect, and the mark is removed in the same change that fixes it.

| from | file under `tests/pile_repro/` | what it pins |
|---|---|---|
| #605 | `test_table_children_phantom_repro.py` | the hook check never looks at Dad's table, so a missing script there is not reported |
| #607 | `test_merge_gate_refuses_printed_merge_repro.py` | the merge guard refuses the merge the stamp prints, and judges switching auto-merge off as a merge |
| #609 | `test_bell_rearm_not_on_exit_list_repro.py` | the doorbell re-arm a gate prints is missing from the shared exit list |
| #610 | `test_action_claims_miss_fixed_saved_written_repro.py` | the action-claim gate does not hear "I've fixed", "I've saved", "I've written" |
| #602 | `test_pipe_and_command_shape_guards_repro.py` | the pipe guard and the command classifier misread some shapes |

Each file's plan note (the helper's own explanation) comes with it under `docs/drafts/`.

## What changed since Aletheia read them, and why it matters

Run against main as of 2026-10-11, one file no longer behaves as it did on 2026-10-08, because #619 landed in between:

1. **Two rows turned into passes.** `echo "divineos audit list"` and `git log --grep "divineos prereg"` were `xfail(strict=True)` reproductions of "the classifier counts words inside quotes as a command". #619 fixed that, the two began to XPASS, and strict marks make an unexpected pass a failure. Their marks are removed; they are now the regression pin.
2. **One control turned into a reproduction of a new defect.** `test_control_a_real_command_hidden_in_bash_dash_c_is_still_caught` was a control: a write run through `bash -c "divineos prereg file x --claim y"` must still make the council gate fire. It FAILS on main today (score zero), because the classifier now reads each segment's real head and `bash -c "..."` has head `bash`. That is a regression from #619 (a real command hidden in a quoted string skips the gate), the exact thing the helper's control was written to guard. It is marked `xfail(strict=True, raises=AssertionError)` here with the reason, and a separate small change reads the quoted string as a command and removes the mark.

The note on that control (psf-9c6f5a9c) says the repair "must not let a real command hidden inside `bash -c` through". Nothing in 619's own tests held that line; this file did.

## What it does not do

- It fixes nothing. The defects stay; only their proof is carried.
- The rest of the held requests in the pins family (#601, #604, #606, #608) are not in this package: Aletheia says they are not yet proven for their stated reason.

## Falsifier (an event)

A fix lands for any pinned defect and its test still carries its `xfail(strict=True)` mark: the suite goes red by name, which is the point. Or one of these files fails on main for a reason other than its stated one: then the proof was never alive and that file leaves the package.
