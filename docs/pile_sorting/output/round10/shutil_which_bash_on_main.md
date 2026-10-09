# The 37 lines on main that ask `shutil.which("bash")`, checked one by one

*Round ten, errand three. 2026-10-09, cloud helper. Read-only: I read each file's bash-finding code on main (commit `cbd35baf`) in a separate copy of main. Nothing was changed, run or fixed. Every verdict is a **reading** of the code, not a run: I have no Windows here.*

**A picture.** On Windows, asking the machine "where is bash?" can hand back a do-nothing stand-in (a doorbell that rings in an empty house). A test is *safe* if it either tries the key before using the door, or refuses the stand-in by name, or gives up with a clear skip when there is no real bash. A test is *dangerous* if it takes whatever the machine hands back and runs it without trying it.

**What I found.** The count is 37 lines in 34 files (earlier I said 36: I had not counted the house finder's own line). Of those, 3 lines are only words in a comment and 1 is the house finder itself, so 33 lines do real work.

| Verdict | Lines | What it means on a Windows machine whose only bash is the stand-in |
|---|---|---|
| **DANGEROUS, group A** | 3 | Takes the answer from `which` and runs it. No try-out, no refusal of the stand-in. |
| **DANGEROUS, group B** | 8 | Looks in the usual Git Bash folders first, then falls back to an unchecked `which`. Fine on a machine with Git installed in the usual place; dangerous where it is not. |
| Safe, refuses the stand-in by name, then skips | 7 | The folder name `System32` is refused; no other bash means a clean skip. |
| Safe, tries the key, then skips | 7 | Runs `echo ok` (or `exit 7`) first; no working bash means a clean skip. |
| Safe on Windows, skips | 1 | On Windows it only looks in the Git folders and returns nothing if they are empty; `which` is reached only off Windows. |
| Safe, tries the key, then **fails loudly** (not a skip) | 7 | Never runs the stand-in. But with no working bash the test goes red, on purpose ("untested, not passing"), where you asked about a skip. |
| Not a test of anything | 4 | The house finder (1) and three comments that mention the name (3). |

## Dangerous ones first

### Group A: takes `which` and runs it

| File | Line | Verdict | Where it is run |
|---|---|---|---|
| `tests/test_hooks_run_in_worktrees.py` | 25 | **DANGEROUS.** `BASH = shutil.which("bash")`; skips only if `None`. | line 49 runs the installer script with it |
| `tests/test_the_doorbell_rings_on_a_new_letter.py` | 20 | **DANGEROUS.** Same; skips only if `None`. Also writes a second bare `bash` *inside* the command string (line 37), which Git Bash would resolve with its own path, so I think that part is lower risk. | line 37 |
| `tests/test_stragglers_coverage.py` | 97 | **DANGEROUS.** `bash = shutil.which("bash")`; skips only if `None`; then runs `[bash, "-n", hook]`. Its docstring says the skip is for "where the WSL bash bridge isn't available", but a present stand-in is not "absent". | about line 105 |

### Group B: Git folders first, then an unchecked `which`

| File | Line | Verdict |
|---|---|---|
| `tests/test_family_wrapper_required_hook.py` | 50 | **DANGEROUS if Git Bash is not in the usual folders.** Its own comment says "may pick WSL on Windows". Skips only on `None`. |
| `tests/test_remedy_allowlist.py` | 290 | **Same.** Skips only on `None`; otherwise runs the `which` result. |
| `tests/test_hooks_import_their_own_checkout.py` | 43 | **Same.** |
| `tests/test_check_push_readiness_failure_surface.py` | 47 | **Same.** (Tries `C:\Program Files\Git\bin`, `/bin/bash`, `/usr/bin/bash` first.) |
| `tests/test_push_gate_substrate_scope.py` | 47 | **Same.** |
| `tests/test_push_gate_tag_only.py` | 69 | **Same.** |
| `tests/test_check_branch_freshness.py` | 43 | **Same.** On Windows it tries three Git folders, then falls through to `which`. Its docstring names the stand-in at `C:\Windows\System32\bash.exe`, so the author knew; the fall-through is unguarded. |
| `tests/test_ci_check_guardrail_trailer.py` | 41 | **Same,** and `which` is the *last* candidate with no refusal of the stand-in. |

## Safe, in three shapes

### Refuses the stand-in by name (`System32`), skips if nothing else

`test_dreams_cross_to_the_shared_room.py:40`, `test_advisory_hooks_stay_advisory.py:45`, `test_front_door.py:432`, `test_lib_worktree_src_reaches_the_hook.py:28`, `test_read_gate_lets_a_look_through.py:34`, `test_yes_and_principle_has_three_homes.py:175`, `test_push_message_carries_the_destination.py:53`. All skip when no usable bash is left. This refusal is by *folder name*, not by trying the key, so a stand-in installed somewhere else would pass it.

### Tries the key, then skips

`test_the_push_wrapper_reads_both_halves_of_a_refspec.py:57`, `test_the_commit_prime_reads_every_segment.py:47`, `test_hook_syntax_surface.py:36`, `test_a_merge_cannot_commit_past_its_own_tests.py:48`, `test_a_push_cannot_outrun_its_own_gates.py:40`, `test_the_context_hook_must_actually_emit.py:88`, `test_the_doorman_holds_without_its_library.py:48`.

### Safe on Windows (skip)

`test_check_cleanup_period_hook.py:39`: on Windows it only looks in two Git folders and returns nothing if they are empty, so `which` is reached only off Windows.

### Tries the key, then **fails loudly** instead of skipping

`test_the_ear_can_tell_wrote_last_from_is_waiting.py:43`, `test_a_push_verdict_cannot_outlive_the_truth.py:42`, `test_unsaved_writing_is_quiet_until_a_commit_goes_past_it.py:45`, `test_the_closing_line_says_which_cycle_it_closed.py:50`, `test_parking_work_says_how_much_is_already_parked.py:59`, `test_a_tag_push_is_not_asked_branch_questions.py:81`, `test_a_door_still_refuses_without_its_library.py:81`. These never run the stand-in; with no working bash they go red with a message. That is a choice the authors wrote down (their reasoning: a skip would leave the file green and empty). It answers a different question from the one asked, so I list it separately and do not call it either safe-skip or dangerous.

## Not a test of anything

`tests/_bash_resolver.py:70` is the house finder itself (it tries the key). Comment-only mentions: `test_family_wrapper_required_hook.py:36`, `test_the_context_hook_must_actually_emit.py:76`, `test_check_branch_freshness.py:29`.

## What I did not do, and where this could be wrong

- **No Windows.** Every verdict is from reading code. "Dangerous" means: the code would run an unchecked answer from `which`. I did not run any of them with a stand-in on the path.
- **Group B depends on the machine.** On a machine with Git for Windows in the usual folders, those eight find the real bash first and never reach `which`. I did not check where Git is installed on any machine but Linux.
- **Bare `bash` that is not from `which`** (for example `bash` typed inside a command string a test hands to a hook) is a different slip and not in this table; the doorbell file is the one place I saw it run, noted above.
- I did not read each file to the end, only the bash-finding code and how its result is used. A second finder in the same file would be missed.
- The round-nine table covered my pull requests; for main it only gave a count. This is the first look at the main files themselves.
- **One guard note:** while collecting this I used a search that contained the word for the test program inside quotes, and the "don't run the whole suite" guard refused it as if I were running the suite. That is a false fire, not a finding about these files, and it is in the errand-five note.
