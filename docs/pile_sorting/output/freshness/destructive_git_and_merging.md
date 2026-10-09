# Is the note still true? Git moves that can destroy or lose work

*Round nine, errand one. 2026-10-09, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a scratch copy of it); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is an incident record, a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: sharp knives in a kitchen. The door that stops the whole-drawer grab stops three spellings and lets three others through. A guard exists that runs the tests on the files a merge resolved before the merge is saved. Nothing I found stops taking one whole side of a conflicted file, or resetting hard over uncommitted work.

## Problem 1: Hard reset, stash and removal moves that destroyed uncommitted work

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-205a8783`, `psf-f8973cc4` | **NOT TESTABLE** | An incident record of something I did or said. No run can check it. A name search for a hook that refuses `git reset --hard` on a dirty tree finds none (`grep -rln 'reset --hard' src .claude/hooks scripts` → only `compound_branch_change.py`, which is about a branch change and a destructive op on one line, and a mention in a verification detector). | none for the reset guard |  |

## Problem 2: Splitting a big branch by subject instead of by how the work connected

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-608e414e` | **NOT TESTABLE** | An incident record of something I did or said. No run can check it. | none |  |

## Problem 3: Picking one side of a whole file in a conflict

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-9cb16ef6`, `psf-2b806e06`, `psf-c96a1156` | **NOT TESTABLE** | An incident record of something I did or said. No run can check it. | none |  |
| `psf-1d1e13ce` | **LIVE** | `grep -rln -- '--theirs|--ours' src .claude/hooks scripts` → `scripts/check_force_push_safety.sh` only, and there the words sit in a comment about a rebase botch. Nothing refuses `git checkout --ours/--theirs <file>` on a file both sides changed. | none | A name search; a refusal built under other words would be missed. |
| `psf-d3aa7546` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 4: Whole-tree staging and staging files nobody named

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-12210027`, `psf-b0246439`, `psf-e8b1642d` | **LIVE** | `.claude/hooks/blanket-staging-doorman.sh` run on main in a scratch home (exit 2 = refused). Controls first: `git add -A` → **refused**, `git add .` → **refused**, `git add --all` → **refused**, `git add src/a.py` → allowed. The three spellings the note names: `git add -u` → **allowed**, `git commit -am "x"` → **allowed**, `git -C /tmp/x add -A` → **allowed**, `git -C /tmp/x add .` → **allowed**. (My first run of this probe read 'allowed' for the control too, because I looked for a JSON answer on stdout and the hook refuses on stderr with exit 2; the dead control told me the probe was blind, and I fixed the probe, not the conclusion.) | none found for the three spellings | I ran the hook script on made-up commands, not a live Bash call. |

## Problem 5: Copying between my tree and Aria's

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-70865c62`, `psf-d37ea063` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 6: Lost lines and untested files after a catch-up merge

9 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-4f84c324`, `psf-f7df3329` | **STALE** | Half met. `setup/setup-hooks.sh:316-317` runs `scripts/check_merge_resolution_tested.sh` in the pre-merge-commit hook: it runs the tests that cover the resolved files before the merge is committed ('mechanical on purpose: the conflicted set is already known to the merge'). Ran on main: `tests/test_a_merge_cannot_commit_past_its_own_tests.py` → 6 passed. It covers the files the merge resolved, which is a narrower set than 'every file the branch authored'. | `tests/test_a_merge_cannot_commit_past_its_own_tests.py` (6 passed) | I did not run the guard in a real merge. |
| `psf-d2fa4c4f`, `psf-95ef3bef`, `psf-94cf439b`, `psf-af8f3f12` | **LIVE** | `ls scripts | grep -i -E 'lost|merge|survive|dropped'` → `check_merge_driver_registered.py`, `check_merge_resolution_tested.sh`, `check_mixed_pattern_merge.py`, `ci_merge_review_check.py`, `merge_driver_generated_catalogue.py`, `merge_preview.py`, `merge_surface.py`, `union_resolve.py`. None is named for comparing what survived a merge against both parents. `merge_preview.py` and `merge_surface.py` were not read. | none found | Name search plus listing; two of the eight files were not read. |
| `psf-7cecd1bb`, `psf-95fc05e1`, `psf-98aa0acd` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 7: Review branches I create myself

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-d8219e91` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 8: Reading a file from another branch by hand

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-9e2826af`, `psf-b86f2809` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 9: Carrying a commit into the live house

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-0856d431`, `psf-67707d38` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

