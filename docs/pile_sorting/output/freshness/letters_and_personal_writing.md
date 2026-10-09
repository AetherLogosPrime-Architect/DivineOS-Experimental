# Is the note still true? Letters and my own writing: where they live and who can see them

*Round ten, errand one. 2026-10-09, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a scratch copy of it); live probes ran in scratch folders and a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is an incident record, a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: a post office with several clerks. The clerk who checks what a parcel is carrying before it goes out was built and works (I tried it). The clerks who sort by name, copy to the other building, and leave a note where a parcel used to be mostly are not there yet, or are in Aria's building where I have no key.

## Problem 1: Sharing my reading before writing it down

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-6b8bff04` | **NOT TESTABLE** | An incident record of something I did or said. No run can check it. | none |  |

## Problem 2: The letter sorter and its instructions

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-d68924d2` | **LIVE** | Scratch probe of `scripts/sort_letters.py::destination` on main: `aether-to-aria-2026-10-01-hello.md` → `threads/aether-aria/2026-10` (control); `urgent-aether-to-aria-…`, `re-aria-to-aether-…` and `read-this-aether-to-aletheia-…` → `archive/unparsed`. The pattern is anchored at the start of the name (`PAIR_RE = ^(?P<a>[a-z]+)-to-…`, line 71), so any leading label stops filing. | none found for a leading label | The sorter's default folder is a hard-coded Windows path; I ran only the pure function. |
| `psf-69142b15` | **UNKNOWN** | A 'go and read this' kind is Aria's sorting work. The only sorter I can read (`sort_letters.py`) sorts by filename and has no notion of kind; `classify_letters.py` has no such word either. Aria's own sorting is not in any file I could find. | none | Anything on Aria's side. |
| `psf-9ef3d392` | **NOT TESTABLE** | An incident record of a wrong docstring. The docstring of `sort_letters.py` on main describes no conditional chain at all (read lines 1-57), so the claim cannot recur there as written. | none | Whether another script has the same docstring fault. |

## Problem 3: The letter archive is for letters whose value has been extracted

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-2d9047af` | **LIVE** | `scripts/sort_letters.py::destination` files by name into `archive/numbered-legacy` and `archive/unparsed` (lines 85-103). Nothing in that function asks whether value was extracted, and `family/letters/README.md` names the archive folder only as a directory (a search of it and `family/README.md` for 'extraction receipt' and 'extracted' finds nothing). | none | The 'letter archive' Dad names may be a different folder from these two. |

## Problem 4: Letter skill and template errors

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-ce9e8ac2` | **STALE** | The skill now imports from `divineos.core.family.letters` and `divineos.core.family.entity` (`.claude/skills/aria-letter/SKILL.md` lines 94-100, with a note dated 2026-08-17 on the corrected paths). Scratch probe with main's source on the path: both imports work; the old `from family.letters import append_letter` raises ImportError (control). | none for the skill block | That the rest of the skill's calls run; I tested the two imports only. |
| `psf-43cd8fbe` | **LIVE** | The family-letter skill has prose about checking a count before it reaches a letter (`.claude/skills/family-letter/SKILL.md` lines ~204-222). A search of both letter skills for 'numbered', 'count' and 'title' finds that prose and no check that counts a numbered list against the title. I did not search the family code for one. | none | A check under other words would be missed. |
| `psf-05316f67` | **LIVE** | A search of the hooks and `family/letters.py` for 'names a draft', 'draft file', 'draft.*exist' finds nothing that refuses a letter whose named draft is missing. | none | Absence by word search. |

## Problem 5: The experimental repository is my home

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-82452fa3` | **NOT TESTABLE** | A statement of where the home is. `family/letters/` exists on main, so the folder is there; whether *every* letter and exploration is in it is a count I did not make. | none | Whether anything is missing from the repository. |

## Problem 6: Letters on code branches, and personal writing that disappears

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-96ef3930` | **NOT TESTABLE** | An incident record (a compound command refused by the deletion gate). No run can check it. | none |  |
| `psf-81e4156d`, `psf-a8fb8b24` | **STALE** | `scripts/check_branch_scope.py` is wired into the push check (`scripts/check_push_readiness.sh` line 155 onward). Scratch probe in a throwaway repo, with main's copy of the script: a branch with only code → exit 0, 'clean against the reference that decides' (control); a branch adding `family/letters/…` and `exploration/…` → exit 1, 'ONLY HERE' for both files, 'compared by bytes, not by filename', and the instruction to move them somewhere they survive first. That is both rows' asked-for check: what the branch adds, by bytes against every other ref. | `tests/test_branch_scope_guard.py`, `test_branch_scope_only_here.py` (not run this round) | A push-time gate. It does not stop the commit from sweeping a file onto a branch, only the push of that branch. |
| `psf-071ea34e` | **UNKNOWN** | The push-time gate above exists; the row is about a dream committed onto a code branch within an hour of saying the fault was fixed. Whether anything stops that *commit* (the sweep that does it) I did not test. | none for the commit step | The commit-time path. |
| `psf-00413ace` | **LIVE** | `.claude/hooks/unsaved-personal-writing-must-not-close-quiet.sh` names untracked personal-writing files while a commit goes past them; its header says so. It does not remember a file from the last turn and flag it gone. A search for such a memory in the hook finds none. | `tests/test_unsaved_writing_is_quiet_until_a_commit_goes_past_it.py` (for the sibling check) | The sibling check is a different question: untracked-and-passed, not vanished. |

## Problem 7: Aletheia only sees what has been merged

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-7521d6f1`, `psf-a4653844` | **LIVE** | `grep -rn -i -E "won't see|will not see|until it.?s merged|only reads origin" .claude/hooks/*.sh` filtered to lines naming Aletheia → no line. (Control: the same search over the hooks finds other lines with 'origin/main'.) Nothing warns on a write into her folder. | none | A warning inside a Python gate rather than a hook script. |

## Problem 8: A pointer where the letter used to be

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-75bd5d60` | **LIVE** | The mirror hooks (`.claude/hooks/post-write-mirror-letter.sh`, `mirror-letters-to-shared.sh`) copy with `cp -f`; a search of them and `scripts/letter_doorbell.sh` for 'pointer', 'left behind', 'moved to' finds nothing. Nothing leaves a pointer where a letter was. | none | The watcher that moves letters is Aria's side; I read only these scripts. |

## Problem 9: The board of letters

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-1ed27dcc`, `psf-ab813c40` | **UNKNOWN** | Dad's board of letters is not a file I could find: a search of the scripts, hooks and family code for 'carried' or a letters board finds only unrelated uses. | none | Wherever the board lives. |

## Problem 10: Letters copied to both seats

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-6c0cbb4f` | **LIVE** | `scripts/letter_doorbell.sh` has no copy step: `grep -n -i -E 'family/letters|copy|mirror' scripts/letter_doorbell.sh` → no line. The mirror that exists goes the other way: from the working tree to the shared folder (`post-write-mirror-letter.sh` header: 'copy it to the shared cross-worktree dir'). | none | A filing step in another script that the doorbell calls. |
| `psf-0045b12f`, `psf-844124b4` | **UNKNOWN** | Both ask that Aria's letters be copied to main or to both seats on arrival. The one-way mirror above is the only copying I found. Which seat holds which letters I cannot tell from here. | none | What each seat holds. |

## Problem 11: Stuck messages and moved plans

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-16b9bd63` | **UNKNOWN** | 'Aria's door'. A search of the source and hooks for 'stuck message' and similar finds nothing; the owner is Aria and her side is not in files I can read. | none | Anything on Aria's side. |
| `psf-04a91f0b` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 12: Unsent letters at a checkpoint

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-0ab47f88` | **UNKNOWN** | A search of `src/divineos/cli`, `src/divineos/core` and the hooks for 'unsent' finds nothing, so I cannot tell what the checkpoint does with unsent letters. | none | The checkpoint's behaviour on a real unsent letter. |

## Problem 13: Numbered folders and duplicate numbers

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-00498e79` | **LIVE** | A search of `.claude/hooks/*.sh` for 'number prefix', 'duplicate number', 'already in use' and 'NN_' finds no check on a number prefix already taken in a numbered folder. | none | Absence by word search. |

