# Every place my open drafts start a program by its short name

*Round nine, errand three. 2026-10-09, cloud helper. Read-only: I changed nothing in this errand. I read the test files my open draft pull requests add or change (the ones from this window, branches `cloud/*`) with two separate searches, listed below, and checked each hit by eye.*

**A picture.** When a test says "run bash", the computer has to decide which bash. On the Windows machine there are two: the real one (Git's) and a do-nothing stand-in that answers "no" and leaves. Naming the program by its short name lets the computer choose, and on Aria's machine it chooses the stand-in. The house already keeps a finder (`tests/_bash_resolver.py`, `bash_executable()`) that tries each candidate and keeps the first one that actually answers. This is the list of my tests that call a program by its short name, and which of them use the finder.

## How I found them (two doors, not one)

1. A pattern for a program named by a bare string where a program path belongs: `["bash"`, `["sh"`, `["python"`, `["git"`, `shutil.which("…")`, and `subprocess…("bash …")`.
2. A second, wider search of the same files for any line that starts a process or names a shell: `subprocess.run/Popen/call/check_output`, `os.system`, `shell=True`, `"bash"`, `"sh"`, `shutil.which`, `sys.executable`.

The second door found no start the first had missed; it also surfaced two lines that are not starts (a docstring and a comparison inside a stand-in; see the notes). Controls: the first search finds the known bare `"bash"` in #608 and #609, so it is alive; and it finds the finder's use in #602, #604 and #614, so it reaches those files.

## The table (15 pull requests searched: #599, #600, #601, #602, #604 to #610, #612 to #615)

| PR | File | Line | Starts | Bare name? | Uses the house's finder? | Risk on Windows |
|---|---|---:|---|---|---|---|
| #608 | `tests/pile_repro/test_look_strict_grep_no_match_repro.py` | 31 | `["bash", str(LOOK)] + …` | **bash, bare** | **no** | **the trap**: finds the stand-in |
| #609 | `tests/pile_repro/test_bell_rearm_not_on_exit_list_repro.py` | 33 | `["bash", "-c", script, "_", payload]` | **bash, bare** | **no** | **the trap**: finds the stand-in |
| #602 | `tests/pile_repro/test_pipe_and_command_shape_guards_repro.py` | 42 | `[BASH, str(HOOK)]` | no | yes (`bash_executable()`) | none from this line |
| #604 | `tests/pile_repro/test_push_wrapper_full_path_refspec_repro.py` | 72 | `[BASH, str(WRAPPER), "origin", refspec]` | no | yes | none from this line |
| #614 | `tests/before_pictures/test_detect_andrew_build_request_before.py` | 135 | `[BASH, str(SCRIPT)]` | no | yes (fixed in round nine) | none from this line |
| #614 | `tests/before_pictures/test_load_dad_ranking_clause_before.py` | 57 | `[BASH, str(SCRIPT)]` | no | yes (fixed in round nine) | none from this line |
| #614 | `tests/before_pictures/test_no_cliff_anchor_surface_before.py` | 49 | `[BASH, str(SCRIPT)]` | no | yes (fixed in round nine) | none from this line |
| #615 | `tests/pile_repro/test_ranking_clause_heading_gone_repro.py` | (the `run_hook_over` start) | `[BASH, str(HOOK)]` | no | yes | none from this line |
| #601 | `tests/pile_repro/test_council_walk_gate_repro.py` | 293 | `["git", "init", "-q", …]` | git, bare | not applicable | low: git for Windows is normally on the path |
| #604 | `tests/pile_repro/test_push_wrapper_full_path_refspec_repro.py` | 43, 48, 57, 84 | `shutil.which("git")` (a skip guard); `["git", *args]`; `["git", "init", …]`; `["git", "ls-remote", …]` | git, bare | not applicable | low, as above |
| #614 | `tests/before_pictures/test_load_dad_ranking_clause_before.py` | 66 | `["git", "init", "-q", …]` | git, bare | not applicable | low, as above |
| #615 | `tests/pile_repro/test_ranking_clause_heading_gone_repro.py` | 58 | `["git", "init", "-q", …]` | git, bare | not applicable | low, as above |
| #612 | `tests/pile_repro/test_cutaway_label_chosen_by_word_repro.py` | 47 (inside a text block that becomes a test) | `[sys.executable, '-c', …]` | no, `sys.executable` | not applicable | none (the right way to start Python) |

No other pull request in the list (#599, #600, #605, #606, #607, #610, #613) adds a line that starts a process. No test in these files starts `python`, `python3` or `sh` by a bare name.

Two hits that are **not** starts, so nobody counts them: `test_detect_andrew_build_request_before.py:17` is a docstring that quotes `subprocess.run(["divineos", ...])`, and `:53` is a comparison `cmd[0] == "divineos"` inside the small stand-in that catches that call. The stand-in does not start `divineos`; it receives the call from the script under test.

## What stands out

- **The slip is in exactly two files, both mine, both written in round seven:** #608 and #609. Both call `["bash", …]` and neither uses the finder. They would fail on the Windows machine for the same reason my first #614 tests did. I have not changed them (this errand is read-only); say the word and they get the same repair as #614.
- Bare `git` appears seven times in four files. It is not the same trap (the stand-in is a problem for `bash`, not `git`), but it is a bare name, so it is listed.
- Every other `bash` start in these drafts already goes through `bash_executable()`.

## A pointer outside my drafts, not part of the table

On main, `git grep 'shutil.which("bash")' -- tests` finds **36 lines in 34 test files**, and 12 test files use `bash_executable()`. Some of the 36 are the house's own probes (they try Git's folders first, `tests/test_hook_syntax_surface.py:36`, or they skip when bash does not answer); others only call `shutil.which("bash")` and use the result. I did not read the 34 one by one, so I do not say how many are the trap. It is the larger list for whoever wants one.

## A guard that would stop the slip coming back (a proposal, not built)

A test that fails when any file under `tests/` contains `["bash"`, `["sh"` or `["python"` as the head of a program list (or starts a process with `shutil.which("bash")` and no finder). Searched on main today, the pattern `["bash"` appears only in the docstring of the finder itself, so such a guard would pass today and catch the next one. I did not write it; the repo's own rule is that a failure found is a fix owed as structure, so it is named here for the owners.

## What this could not do

- I only searched the 15 pull requests that are from this window; the 16 other open drafts (branches `aria/*`, `fix/*`, `docs/*`, `rebuild/*`, `salvage/*`) are not mine to scan in this errand and were not searched.
- I read the test files as text. I did not run anything on Windows.
