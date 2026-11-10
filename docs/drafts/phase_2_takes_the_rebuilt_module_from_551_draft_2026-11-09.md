# Phase 2 takes the rebuilt module from #551 (draft, 2026-11-09, Aria)

Status: DRAFT. Walk in the chat, Aether's cold read, tests first, then code. Nothing is changed by this note.

## What happened

Two pull requests carry one module, `auto_cycle_phase2.py`, and cannot both merge (add/add on the module and its tests; 673 lines differ in the module, 921 in the tests).

- **#753** (`aria/auto-cycle-phase-2-rest-and-dream-menu`): the July build brought onto today's main, with its commands in a separate file `auto_cycle_phase2_commands.py`, patched on 11-03 after the first reader.
- **#551** (`salvage/from-the-four-2026-09-22`): the same module rebuilt on 2026-09-25 after Aether's station four, with its commands inside `auto_cycle_commands.py`, plus two later commits (`b64f4f897` on 10-12, `bb3aa0bf3`) and a main-slice merge on 10-28.

Eight findings branches (754, 782, 787, 791, 793, 797, 798, 799) review these two. I re-ran their probes against both modules in isolated homes on 2026-11-09. Results (`~/.divineos-shared/workbench/findings_on_753_status_2026-11-09.md`, section H):

| Case | #753 | #551 |
|---|---|---|
| Main's dry run (every step `ran=False, succeeded=True`) | accepted as completed | refused |
| `cycle_id: null` | accepted as the text "None" | refused |
| `1e999` in an integer field | raises `OverflowError` | raises `OverflowError` |
| `true` where a number belongs | accepted as 1 | accepted as 1 |

Aether checked my list against what he recorded on 2026-09-25 (`bc423d35`, `7d1df2b6`, the rebuild's commit `6c577d2fd`) and agrees the rebuilt module is the base.

## The change

**The module that survives is #551's.** It is brought into #753's branch and the branch is the one that goes forward; #551 is closed with a pointer afterwards.

1. `src/divineos/core/auto_cycle_phase2.py`: replaced by #551's version, including its two later commits and the 10-28 main-slice merge.
2. `src/divineos/cli/auto_cycle_phase2_commands.py`: kept (#753's separate file, as `__init__.py` wires it), adapted to #551's names (`inspect_handshake`, `refusal_text`, `parse_outcome`, `no_pull_count`, `damaged_audit_line_count`), so `auto_cycle_commands.py` stays phase 1's and phase 2 does not grow into it.
3. `tests/test_auto_cycle_phase2.py`: both suites merged by behaviour, not by file. Where both test a thing, the stricter test stays. #753's 71 tests are read for what they pin before any is dropped.
4. **Fixed once, in the surviving module, with a test that fails on the old code:** infinity in an integer field returns None (`OverflowError` joins the tuple), and a boolean is not a number (`float(True)` and `int(True)` are refused).
5. **One UTC duration repair, not two:** #753's `74a609c7d` and #551's `bb3aa0bf3` are the same repair; keep #551's, delete #753's.
6. **Carried from Aether's non-blocking list:** the stale "11 REST_TASKS" docstrings and the lower-case Author line (not checked by either of us; a read when I make the change); the double-log after a crash between the audit write and the unlink (no cycle-id check before appending; rare, fails toward more evidence, so it goes on the list and does not block).
7. **Stale text** from the readers' findings: the module docstring and `auto_cycle.py:37` still name `~/.divineos/auto_cycle_phase1_done.json`; the outcome comment omits `superseded` if that outcome survives (it may not, since #551 consumes the handshake at close and a re-offer is then the same cycle).

## Changed by the walk (walk-c1e91a70c961, nine lenses, written in the chat first; distinctness mean 0.389, max 0.633 between Schneier and Taleb, reported and not read either way)

- **Take #551's module WHOLE, not blended line by line** (Taleb). 673 lines differ; a hand-picked line is a place to go wrong unseen. From #753 only the separate CLI file survives, adapted. The two shared faults are the only edits to the module.
- **The reviewers' probes become permanent tests written from the findings, not from my old belief** (Dennett, Dawkins): the four rows of the table plus infinity and booleans, so a later copy cannot bring the flaw back unnoticed.
- **One strict meaning of "completed", stated in exactly one place** (Wittgenstein, Dijkstra): every step says in booleans that it ran. The menu, the offer and the close all use that one decision. The CLI file may only translate and makes no decision of its own.
- **The test that matters most goes through the command** (Schneier): the CLI adapter is the new code that belongs to neither suite, so a test feeds the command the dry-run marker and expects a refusal.
- **An unanswered offer stays visible** (Beer): #551 consumes the handshake at close, so the note stays in place until the cycle closes. My 11-03 `superseded` outcome made abandoned offers vanish into a row the ratio skips; it goes unless something in the surviving flow still produces it.
- **No thresholds are touched** (Meadows). Whether skipping should ever go red is a decision for Aether and Dad.

## Added by Aether's cold read of this draft (2026-11-09)

- **#551 also changed phase 1's `fire` command, and the plan would have lost it.** In `auto_cycle_commands.py` #551 prints `DRY` for a step that never ran (`"DRY" if not step.ran else "OK " if step.succeeded else "FAIL"`), with a comment saying why: a dry run reports `succeeded=True` on steps that never ran. Main's `fire` and #753's both print `OK`. So after the module change, the reader would refuse a dry-run marker while `fire --dry-run` still showed four green OKs: the reader fixed and the display not (half of his station-four finding 1). **Carried as its own item, one line in `auto_cycle_commands.py`, with a test that a dry run prints `DRY`; the test belongs with the command and fails on main today.**
- **`superseded`: nothing outside the module reads it.** In #753 it appears only inside the module and its own tests (lines 401, 402, 456, 486, 571, 591; tests 545 to 561 and 586). #551 has none. Dropped, with those tests, each with its reason written down.
- **#753's separate CLI file stays; #551's `offer`, `close` and `audit` in `auto_cycle_commands.py` must not come over** (the commands would register twice; the registration test keeps this). The adapter is smaller than first written, with one addition from reading #551's version of the commands: its `offer` prints the refusal text (`absent`, `malformed`, `did-not-run`) when there is no usable handshake, and its `close` catches `DamagedPending`. Those two behaviours belong in the separate file, since the module now raises and returns them.
- `read_handshake()` stays in #551's module (line 214, a thin wrapper); I check who calls it before deciding it stays.

## Built (branch aria/auto-cycle-phase-2-rest-and-dream-menu, 2026-11-09)

- Module: #551's rebuilt `auto_cycle_phase2.py` whole, then three additions: infinity and booleans in a count make the marker `malformed` (the count was silently zero before, and `OverflowError` escaped), `repo_root` carried into the audit summary (from #753; older markers read as ""), and the absent-marker refusal names the folder this house really reads.
- Commands: `auto_cycle_phase2_commands.py` kept as the place phase 2 registers, with #551's behaviours (the three-way refusal text, `DamagedPending`, `no_pull_count`, damaged audit lines); phase 1's `fire` prints `DRY` for a step that never ran.
- Stale text: `auto_cycle.py:37` no longer says the marker lives in `~/.divineos`; the module docstring #551 wrote already used `marker_path()`.
- Tests: 109 pass across the new probe file, #551's suite (65) and phase 1's. Four breaks applied one at a time (dry run believed, `true` as a number, infinity raising, `fire` printing OK for a dry run) failed 4, 3, 4 and 1 tests, and restored passes.

### #753's old tests that were dropped or replaced, with the behaviour each pinned

| Old test (#753) | What it pinned | Where it went |
|---|---|---|
| `test_offer_deletes_handshake_marker` | offer consumes the handshake | opposite behaviour now; #551's `test_offer_leaves_the_handshake_for_the_close` |
| `TestMissingMeansNotCompleted` (step without `ran`/`succeeded`, not a mapping: "counts as failed") | a malformed step still yields a result flagged failed | stricter now: refused as `malformed` or `did-not-run`; #551's `test_a_marker_that_does_not_state_itself_is_malformed`, `test_a_real_dry_run_is_refused_as_did_not_run` |
| `TestAnUnclosedOfferingIsNotSilentlyOverwritten` (5 tests) | a re-offer is logged `superseded` and skipped by the ratio | the `superseded` outcome is gone (nothing outside the module read it); #551 refuses a second offer and names the open cycle (`test_a_second_offer_is_refused_and_names_the_open_cycle`) |
| `test_the_duration_does_not_depend_on_the_local_timezone` | UTC duration | #551's `test_the_duration_is_real_time_whatever_the_local_zone` |
| `TestMarkerAbsenceSafety` (4 tests) | no marker, write failure, malformed, wrong type fire nothing | #551's `test_no_usable_marker_fires_nothing` plus a parametrized "not an object" test in the new file |
| `TestTheMenuSaysWhatActuallyHappened.test_steps_that_did_not_run_are_named_as_not_run` | the menu names steps that did not run | unreachable by design: a dry run is refused before any menu is drawn |
| `repo_root` (2 tests), `TestTheRefusalNamesThePathItReallyReads`, pending-and-audit-in-one-home, ran-and-failed named, clean cycle prints no caution | behaviours #551 lacked | **kept**, rewritten by behaviour in the new probe file |

## What I am deliberately not doing

- The **ratio design** (finding E) is not re-decided here: #551's treatment (the numerator is `chose:` with `real_shift`, `no-pull-honest` out of both sides, `no_pull_count()` printed) is taken as it is. Whether skipping should ever go red is a decision for Aether and Dad, written separately.
- The `superseded` outcome I added on 11-03 (`139f95ce9`) belongs to the design #551's consume-at-close replaces. I check whether anything still needs it before dropping it; if #551's flow never produces a superseded row, it goes.

## Tests, first

- The four rows of the table above, as tests that fail on #753's reader and pass on the survivor.
- `1e999`, `-1e999` and `true` as a number return None, in both numeric fields they can appear in.
- A suite-level check that the phase 2 CLI is the only place registering `offer`, `close` and `audit`, so no command is registered twice.
- The merged suite passes on the branch.

## Falsifier

If the survivor accepts any of the four rows of the table that #551 refuses, or raises on infinity, or a test from #753's suite that pinned real behaviour is dropped without its reason written down, the merge is wrong. Cost: the changed head needs Aletheia's re-confirm.
