# Is the note still true? The merge button, the review stamp and the one-command merge

*Round five, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `d310aadc` (a copy in a scratch folder); live probes ran in a scratch home. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters, so a verdict is about what the visible text asks for. Where a standing test exists it is named; the reproductions cited as 'PR #601' and 'PR #602' were re-run against current main.*

A picture: the checkout counter at the end of a shop. Since the notes were written the shop added a self-service lane (`divineos ship`) that checks the receipt and prints the final slip but never rings you through, and a floor-check that lets a basket through if only the shelves moved. What is still missing is mostly in the old counter's rules: it still mistakes 'turn auto-pay off' for 'pay', cannot read a slip handed over on paper, and suggests whichever approval is newest rather than the one for your basket.

## Problem 1: I told Dad things about the merge rules that were not true

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-658d47f2`, `psf-3d183bb6`, `psf-68b14a6a`, `psf-f29a7860`, `psf-b160817f` | **UNKNOWN** | A one-time incident record. Its repair, if any, sits in the correction's own 'structural fix' text, which the pile cuts off. Nothing on main could be pointed at that the row asks for, and nothing could be run to settle it. The proposed fix ('quote the live ruleset line') is behavioural; the live ruleset could not be read (REST rulesets call not attempted from the cloud). | none |  |

## Problem 2: Updating a branch rewrites its head and can undo approvals

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-7c9763d8` | **LIVE** | `grep -rln 'update-branch' .claude/hooks src scripts` → no file, so nothing refuses `gh pr update-branch` on an approved head (control: the same grep style finds `pr merge` in `ship_command.py` and `stamp_ready_command.py`). | none | A hook outside those folders would be missed. |

## Problem 3: The stamp tool asks stale questions, cannot see the evidence, or half-finishes

14 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-ac1a8609` | **UNKNOWN** | Two readings. The house now prints the merge with the trailer written literally (`ship_command.py:101` `button()`; `stamp_ready_command.py:735` prints `--body-file`). But main's merge gate does not read `--body-file` (probe below, problem 5), so the printed form can itself be refused. | `tests/test_ship_command.py` |  |
| `psf-59b0a7fc`, `psf-5346881f`, `psf-b82e1701`, `psf-c46d8629`, `psf-28c278ac`, `psf-d26f83b2`, `psf-9d61119d`, `psf-c10df800`, `psf-fc0ae98d`, `psf-64672d65`, `psf-9d6edd4b`, `psf-70cd98ec`, `psf-75ad3cc2` | **UNKNOWN** | `divineos stamp-ready` cannot be run from a cloud session (GitHub GraphQL is blocked), so a verdict that needs a live stamp run is UNKNOWN. Several also read as design wishes (one command for the owner line, a draft at the start of a build). | none | Needs a running house. I also could not read `audit prepare-merge --help`: the council gate demanded a walk for the help screen itself, which is the help-screens-owe-a-walk problem of PR #601. |

## Problem 4: The reading declaration and station four accept unfit input

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-45ef2f02`, `psf-1495f576`, `psf-3252af7f` | **LIVE** | `src/divineos/core/build_flow.py:236-255` (`_declared_readings`) reads one line, `**Reading:** branch, branch`, and returns branch names only; `:328-345` marks station 4 SATISFIED when the branch is named. No verdict, version, age or opened-test-file is read or checked. | `tests/test_a_wrapped_table_child_wires_its_wrapper.py` is unrelated; none for this |  |
| `psf-c325072a`, `psf-8d07eccd` | **UNKNOWN** | `c325072a` is an incident; main now says when a declaration 'misses its own format' instead of reporting an absent reading (`build_flow.py` station four, around `:616`). `8d07eccd` (template includes the line) not examined. | none |  |

## Problem 5: The merge guard suggests a review round that does not name this request

13 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-49ddcf70`, `psf-5a23f257`, `psf-b73eba54` | **LIVE** | Probe on main's `pr_merge_gate.block_reason` with the PR made to touch a guardrail file and no usable round: control `gh pr merge 5 --squash` → BLOCKED; control with the trailer at a line start inside `--body` → allowed; **`gh pr merge 5 --disable-auto` → BLOCKED**. `grep -rn 'disable-auto' src .claude/hooks scripts` → no file. | `tests/test_pr_merge_gate.py` | Gate also exists as hook `gh-pr-merge-gate.sh`; the Python verdict was probed, not the hook. |
| `psf-ebb90faf`, `psf-b467a6cc` | **LIVE** | Same probe: **`gh pr merge 5 --squash --body-file <file containing the trailer>` → BLOCKED**. `pr_merge_gate.py:206-215` searches the command text only; `grep -rn 'body-file\|body_file'` over the gate modules → no match. The stamp's own printed command uses `--body-file` (`stamp_ready_command.py:735`). | `tests/test_pr_merge_gate.py` |  |
| `psf-f8f11620`, `psf-2b86b575`, `psf-dbf59f42` | **LIVE** | `pr_merge_gate.py:217-333` (`_find_usable_audit_round`) loops over the 50 most recent rounds and returns the first with a user CONFIRMS and an external-AI CONFIRMS inside 14 days; `pr_number` is only used for the fallback focus text. It never compares a round to the request. Open draft #592 ('The merge gate offers only this PR's own round') carries the repair and is not on main. | none on main | `f8f11620`'s second ask (a test that writes into the real project folder) not examined; `dbf59f42`'s 'any quoting' clause not probed. |
| `psf-883f4416`, `psf-669cbc58`, `psf-253ae499`, `psf-5b5e0842` | **LIVE** | Mixed rows. The 'nested in a larger command' clause is **met**: `cd /tmp && gh pr merge 5 --squash` → BLOCKED with the same verdict as the bare form (probe; `pr_merge_gate.py:335-365`, `block_reason`, anchors on command position). The remaining clauses are not: the round is not matched to the request (above), `--disable-auto` is blocked, and `--body-file` is not read. | `tests/test_pr_merge_gate.py` | Counted LIVE because at least one clause still reproduces. |
| `psf-4825bd0e` | **UNKNOWN** | An incident: a PR body containing prose about a trailer. `_TRAILER_PATTERN` (`pr_merge_gate.py:60`) is line-start anchored and `_GH_PR_MERGE_PATTERN` is command-position anchored after quote scrubbing, which addresses the shape, but I did not run the original body. | `tests/test_pr_merge_gate.py` |  |

## Problem 6: The one-command merge

11 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-1786400e` | **LIVE** | `src/divineos/cli/ship_command.py:1-9`: 'It is never run here and auto-merge is never turned on: the machine hands me the button and the press stays mine.' So `divineos ship` is not the only thing that merges; the merge is still typed by hand. | `tests/test_ship_command.py` (39 passed with `test_ship_steps.py`) | The note and the design disagree by intent; the design may be the newer decision. |
| `psf-a9c98be8`, `psf-525005d0`, `psf-c6634d6c`, `psf-75965202` | **LIVE** | `ship_command.py:69-93` (`checks_step`) reads `statusCheckRollup` once (`:37`), the summary list; it does not wait; an empty list is 'no checks have reported on this head yet' with no 'because of a conflict' state; it prints a reason per step but saves no output to a file. | `tests/test_ship_command.py` |  |
| `psf-09c7805e`, `psf-03b37feb` | **LIVE** | `ship_command.py:47-52` (`read_step`) fails a draft ('still a draft') and nothing catches the branch up first; the steps are read, her, floor, user, checks. | `tests/test_ship_command.py` |  |
| `psf-c32ac356` | **STALE** | 'The merge button, the next build' exists as a first cut: `divineos ship <pr>` (`ship_command.py`, landed in `cc4714dc` / #582 'ship, first slice'). | `tests/test_ship_command.py`, `tests/test_ship_steps.py`: 39 passed, 1 skipped | It prints the command; whether it is the 'button' the row means depends on problem 6's other rows. |
| `psf-da3f0c06`, `psf-daa4a3f3`, `psf-10dc51a5` | **UNKNOWN** | Planning and sequencing notes ('the one command, then the three smaller fixes'; 'let the next ten merges test it'); nothing to check on main. | none |  |

## Problem 7: The floor check ('main moved' versus 'changed after review')

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-7ffe1c32`, `psf-92882aaf` | **STALE** | The floor check exists: `src/divineos/core/ship_steps.py:150` (`floor_proven`) and `:191` (`head_is_only`), used as the `floor` step in `ship_command.py:130-170`; it tells 'only main moved' apart from 'changed after review'. The register-only case is tested: `tests/test_ship_steps.py:188` (`test_a_regenerated_register_is_tolerated`). Ran on current main: 39 passed, 1 skipped. | `tests/test_ship_steps.py` | It runs inside `ship`, not 'before the merge' as a separate command. |
| `psf-2b475604` | **UNKNOWN** | 'Compare against the main each branch actually merged, not today's main': `ship_command.py:204-212` fetches `main` and asks whether the merged-in parent is on origin/main 'as THIS computer last saw it', which is today's main, not the branch's. Whether that is the lesson's opposite cannot be told from the visible text. | `tests/test_ship_steps.py` |  |

## Problem 8: Auto-merge turned on without being asked

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-08a797d3`, `psf-f0408a1e` | **LIVE** | `src/divineos/cli/stamp_ready_command.py:835` option `--no-auto-merge` ('Stamp and mark ready, but leave the merge for a person to do') and `:1517-1526`: unless that flag is given, the stamp runs `gh pr merge N --squash --auto`. So auto-merge is on by default. (`ship` is the opposite by design, `ship_command.py:1-9`.) | none |  |

## Problem 9: A red box reached main

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-db08ab87` | **UNKNOWN** | Needs the repository's rulesets and admin-override history; neither is in the code, and I did not read them. | none |  |

## Problem 10: After a merge the next queued piece is left stale, and piece order is remembered by me

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-4d44e8d6`, `psf-f26b0d1f` | **LIVE** | `src/divineos/cli/automerge_commands.py:1-20` is a read-only status surface ('No network writes'); nothing updates the rest of the queue after a merge. `grep -rln 'depends_on\|depends on' src/divineos/cli/ship_command.py stamp_ready_command.py automerge_commands.py` → no file (control: `queue` matches `automerge_commands.py`). | none |  |

