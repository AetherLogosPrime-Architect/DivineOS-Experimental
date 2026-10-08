# The cut-away checker, tried on ten test files in the cloud

*Round seven, errand four. 2026-10-08, cloud helper. Read-only on our side: the checker was run from a separate scratch copy of the branch `aria/the-cutaway-checker` (commit `0fd9afa3`), never against the whole suite, and its baseline file was not written. Nothing was changed.*

**A picture.** The checker is a stage hand who, one test at a time, saws through the leg of the table the test says it is standing on, and watches whether the test falls. A test that stays upright with the leg gone was never standing on that table. I asked the stage hand to try this on ten tests I chose, in a theatre it had not been in before (the cloud), to see whether it could work at all there.

**The short answer.** It ran, on all ten, and said something sensible on all ten. It matched the recorded counts for every one of the ten. It left the scratch copy clean (`git status` showed nothing). It did not hang or crash. I did not time it.

## How I ran it

From a detached scratch copy of the branch, with a scratch home folder so the tests could not touch our real house:

`python3 scripts/cutaway.py --workers 2 --json <out> --files <ten files>`

No `--check`, no `--update-baseline`, no `--all`.

## The ten, and why these

I chose them from the places I had already been in rounds five to seven, plus two I expected to behave differently (a file that scans repository files, and a file that runs hook scripts in a child process), so the trial would meet more than one kind of test.

| # | File | Why I picked it | Ran? | Collected | Functions cut | What it said |
|---|---|---|---|---|---|---|
| 1 | `tests/test_hook_layer.py` | the hook counter's own tests | yes | 12 | 17 | 11 connected; 1 labelled "out of process?" |
| 2 | `tests/test_pr_merge_gate.py` | the merge guard (round-six test) | yes | 22 | 8 | all 22 connected |
| 3 | `tests/test_no_fix_claim.py` | the "no fix" guard (round-six test) | yes | 43 | 92 | 41 connected; 1 disconnected; 1 "other red" |
| 4 | `tests/test_heredoc_escape_check.py` | the heredoc door | yes | 19 | 5 | all 19 connected |
| 5 | `tests/test_gravity_classifier.py` | the command classifier | yes | 70 | 8 | 69 connected; 1 labelled "out of process?" |
| 6 | `tests/test_landed_claim.py` | the "it landed" claim check | yes | 9 | 4 | all 9 connected |
| 7 | `tests/test_ship_steps.py` | the ship floor check | yes | 25 | 9 | 24 connected; 1 skipped |
| 8 | `tests/test_ship_command.py` | the ship button | yes | 15 | 652 | all 15 connected |
| 9 | `tests/test_hook_python_lookup.py` | a test that scans repository files | yes | 2 | 0 | both disconnected |
| 10 | `tests/test_advisory_hooks_stay_advisory.py` | a test that runs hook scripts in a child process | yes | 5 | 0 | all 5 "out of process?" |

Totals reported by the tool: 7 out of process?, 210 connected, 3 disconnected, 1 other-red, 1 skipped (222 tests).

## Does it agree with the recorded floor?

The branch carries `scripts/cutaway_baseline.json` (245 files). For these ten files, the DISCONNECTED and SWALLOWED counts I measured in the cloud equal the recorded floor in every case (for example: `test_hook_python_lookup.py` 2 against 2, `test_no_fix_claim.py` 1 against 1, the rest 0 against 0). Nothing rose above its floor. That is the useful result: the numbers made on the author's machine and the numbers made here agree on these ten.

## What surprised me, or looked broken

1. **"Out of process?" is decided by a word in the file, and two of the three tests it labelled that way run in the same process.** In `analyze_file` the label is applied to every disconnected test in a file whose text contains `subprocess` or `bash` (any case). `test_hook_layer.py` has zero uses of `subprocess`; "bash" appears only inside fixture strings like `"#!/bin/bash\nexit 0\n"`. `test_gravity_classifier.py` has zero `subprocess`; "bash" is the word in the argument name `bash_command`. The two tests it relabelled (`test_the_event_list_is_the_routers_and_not_a_second_copy`, `test_dataclass_default_is_council_required_false`) are plain in-process checks, and both are honestly disconnected (a module-level identity; a dataclass default), so the verdict happens to be harmless. But the baseline counts only DISCONNECTED and SWALLOWED, so a relabelled test never counts against the floor. A new weak test added to any file that mentions "bash" would pass the ratchet unseen. This is the one I would look at first.
2. **One test went red without touching the cut code and the tool did not say why.** In `test_no_fix_claim.py`, `test_the_lens_count_is_distinct_lenses_not_repeats` passed untouched and failed under the cut, with no hits on a cut function; the tool calls this "other red". I did not dig. It may be an honest dependence on a cut helper by another route, or it may be the cut breaking something else.
3. **Zero functions cut is reported as a plain result.** For `test_hook_python_lookup.py` and `test_advisory_hooks_stay_advisory.py` the tool found nothing in the product to cut (`cut_functions` 0), so a "disconnected" there is the honest reading for the first file and "out of process?" is right for the second. It is correct, but the summary line does not show that nothing was cut; I read it from the saved results.
4. **The skipped test is a cloud fact, not a fault.** `test_every_real_confirm_she_has_written_still_reads` skips because Aletheia's letters are not in the cloud copy.
5. **Size.** `test_ship_command.py` cut 652 functions for 15 tests, far more than any other. The run finished, but this is the file I would expect to be slowest.

## What I could not do or did not do

- I did not time the run, so I cannot say how long a ten-file trial takes in the cloud, or scale that to the full suite.
- I used two workers, not four (the default). I did not test the default.
- I did not feed it a test I knew to be weak, to see that it flags it. The trial shows it runs and agrees with the recorded floor; it does not show it catches a new weak test. (That is a second trial and it is not the big sorting job.)
- I did not read `scripts/cutaway_plugin.py` (262 lines), which makes the cut; I read the driver only. I did not read its own tests (`tests/test_cutaway.py`).
- Windows is untested here. The tool's header says it was first written on Windows and had a console-window problem; the cloud has no windows to open, so that fix was not exercised.
- The full suite was not run, and the 1,129-test sorting job was not started.
