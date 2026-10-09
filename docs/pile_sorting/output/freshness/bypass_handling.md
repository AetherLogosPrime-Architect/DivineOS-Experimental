# Is the note still true? The emergency exits I use, and what they cost to explain

*Round ten, errand one. 2026-10-09, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a scratch copy of it); live probes ran in scratch folders and a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is an incident record, a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: the fire doors. The door that cannot be pushed without writing down a reason works and I tried it. The door for 'there is no structure for this' asks only for forty characters of reason, not for the list of structures I looked at. And the branch-check door only follows one way of writing a push; the other ways still measure the wrong folder.

## Problem 1: The 'no structure is possible' exit gets used when a structure exists, or as a shrug

9 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-bc1efbe8`, `psf-798dd6b1`, `psf-6e19ea78`, `psf-14b81a1f`, `psf-ac6c7de4`, `psf-11f69e87`, `psf-0d862c88`, `psf-8d5eb7ec`, `psf-f1e62043` | **LIVE** | `src/divineos/cli/correction_commands.py` (lines 210-215, 284-289, 382-395): the exit is now written 'structure not yet found: <why>' or 'no structure possible: <why>', needs a reason of at least 40 characters, and when taken it files a bypass record with `is_compliance=False` (the alarm) and files the item as UNRESOLVED. It does **not** require naming the specific structures considered and why each fails, which is what the notes ask. Eight of the nine rows use the older name `no-structure-possible`; the last uses `structure-not-yet-found`. Whether the use surfaces to Dad in the briefing, I only know the telemetry feeds a windowed briefing line (`bypass_telemetry.py` around line 561). | none for the naming-the-alternatives part | I read the code; I did not file a correction to try the exit (that would write to the real ledger). Each row is also itself an 'investigation owed' receipt: no run decides whether *that* use was honest. |

## Problem 2: Emergency exit on the 'pre-registration before new machinery' gate, root cause owed

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-a17f5e77`, `psf-687ec1ae`, `psf-e157fade`, `psf-903e6cd9` | **UNKNOWN** | `scripts/check_prereg_for_new_infra.py::_staged_new_files` subtracts anything already present at MERGE_HEAD during a merge (written 2026-07-31 after Aria hit it live; lines 72-110). Scratch probe in a throwaway repo: a module that arrives from the other side of a merge → the gate asks for nothing; a new module staged on a plain commit → asked (control); a module added during a merge that exists at neither parent → still asked (control). **But the rows are dated 2026-08-14 and 2026-08-15, after the fix**, so either their shape was not a plain merge (a squash, a cherry-pick) or their checkout lacked the fix. I cannot tell which. | none found for the merge subtraction by name | The shape of the August merges. |

## Problem 3: Emergency exit on the branch-check at push time, root cause owed

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-a99511db` | **NOT TESTABLE** | A record of a test arm ('confirm the loud mv path still consumes the marker'). No run can check a past test. | none |  |
| `psf-43ba335f`, `psf-4f0d4522`, `psf-3c007dc6` | **LIVE** | Partly fixed. `.claude/hooks/check-branch-on-push.sh` (lines ~270-303) now asks `divineos.core.push_detection.push_cwd` for the tree being pushed and runs `check-branch --cwd` on it. Scratch probe of `push_cwd` with a real git tree: `cd <tree> && git push …` → the tree (works); `git push` alone, `git -C <tree> push …` and `cd <tree>; git push …` → `None`, so those fall back to the session folder, the very fault the rows describe. The kill-switch marker (`check-branch.disabled`, line 131) is also still there; the notes ask for it to be retired. | `tests/test_push_cwd_reads_the_bash_path.py` (pins the `cd … &&` form) | I did not run the hook end to end; I ran the function it calls. The notes do not say which push form was used. |

## Problem 4: Emergency exit on the 'no skipping the commit checks' gate, root cause owed

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-5644371f` | **UNKNOWN** | The doc-count check (`scripts/check_doc_counts.py`) verifies the architecture tree's files exist. Whether it separates 'absent from this branch' from 'wrongly missing' I did not run. | none | Its behaviour on a branch behind main. |
| `psf-16f16a21` | **LIVE** | The only way to a verbatim backup commit past the commit checks is `--no-verify` with an inline reason, which the cost-escalation surface requires and logs (`src/divineos/core/no_verify_cost.py`; probe in problem 8). I found no separate sanctioned backup path that needs no bypass variable: a search of `scripts/*.sh` for 'backup commit', 'verbatim backup' and 'sanctioned' finds nothing (I did not search the hooks for it). | none | Absence by word search. |

## Problem 5: Emergency exit that skipped the tests at push time, root cause owed

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-9993e1bd` | **LIVE** | `scripts/check_push_readiness.sh` lines 391-418: `DIVINEOS_SKIP_TESTS=1` skips pytest and records the bypass with a fixed reason string ('pytest suppressed at push time via the documented emergency bypass'). It takes no reason of its own and leaves nothing for the review step to re-run. | none | A re-run by the review step that I did not look for. |

## Problem 6: Bypass notes that state the wrong cause

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-806b6a3a` | **NOT TESTABLE** | A self-correction record about a wrong stated cause. No run can check it. | none |  |
| `psf-58aa6305` | **UNKNOWN** | `src/divineos/core/bypass_telemetry.py` explains why old rows are left as they are (Dad: 'leaving bad data with nothing explaining its bad is worse than erasing it', lines ~620-630) and prints the corrected and uncorrected windowed lines. A search of the module for a way to attach a correction note to one row finds none, but I read it by word search only. | none | A correction mechanism under other words. |

## Problem 7: Operator-authorised reset of the letters-unspoken door

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-e14356cd`, `psf-7f1f1139` | **UNKNOWN** | The token `bypass:operator-authorized-reset` appears in no file under `src`, `.claude/hooks` or `scripts` (the only near hit is an enum value, `OPERATOR_AUTHORIZED_BYPASS`, in `council_required/types.py:143`). The gate `unspoken_to_letter` is in `hook_surfaces.py`. I could not tell whether a reset records Dad's words or expires when the fix is done. | none | How the reset is granted and stored. |

## Problem 8: Reaching for the skip-the-checks flag without deciding to

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c6dbee9b` | **STALE** | `src/divineos/core/no_verify_cost.py::decide` is registered in the front door (`hook_surfaces.py` lines ~254-325 and 2318). Scratch probe with a scratch home: `git commit -m x` → allowed (control); `git commit --no-verify -m x` → denied; `git push --no-verify origin x` → denied; the same commit with `DIVINEOS_NO_VERIFY_REASON="…"` in front → allowed. So the flag cannot be passed without a typed reason, and the reason is logged on the allow path. | `tests/test_no_verify_cost.py` (not run this round) | That the logged reason reaches a surface Dad reads; the probe used a scratch home. |

