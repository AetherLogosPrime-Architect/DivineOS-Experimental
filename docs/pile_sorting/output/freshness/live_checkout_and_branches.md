# Is the note still true? Which copy of the house I am standing in, and how many branches there really are

*Round eight, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (the working copy or a scratch copy of it); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is a habit, an incident record or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: a map of workbenches and the front house. Most rows are asks for a better map. I found one good guard already built (the python resolver that refuses a cross-install) and two asks that the briefing prompt only half meets. Most of the rest I did not walk.

## Problem 1: A second worktree leaking its install into the first

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-0584e064` | **STALE** | `.claude/hooks/_lib.sh` `find_divineos_python` (about lines 440-458, comment dated 2026-08-13) accepts a python only if the `divineos` it can see lives under THIS repo's `src`. Probe (round eight): in a scratch repo whose `src` was not linked to the one the install points at, the resolver refused ('python_resolve_failed: no viable python'); with `src` linked it accepted. Control: the same hook ran normally in the real repo. | `tests/test_hook_python_lookup.py` (scans hooks for the helper; not the refusal itself) | It stops a hook from running the wrong checkout's code. It does not make two installs separate. |

## Problem 2: The branch-scope and deletion checks mislead

7 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-21d12a91`, `psf-367d2f95`, `psf-6ab9255a`, `psf-fa0ee43a` | **NOT TESTABLE** | An incident record of something I said or did. No run can check it. | none |  |
| `psf-fc538de9`, `psf-08321409`, `psf-fccf9086` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 3: Setting up and finding the right workbench

8 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-9bca231f`, `psf-d5ee412f` | **LIVE** | `ls scripts | grep -iE 'worktree|workbench|workspace'` → `ready_pr.sh` and `check_push_readiness.sh` (both create a worktree for their own job); `grep -rln 'worktree add' scripts .claude/hooks` → the same files plus the automation register generator. No command that lists a branch's existing workbenches before making one, or reuses one. Control: the grep finds those scripts, so it reaches the folder. | none | A name search; a helper under another name would be missed. |
| `psf-1630eb78`, `psf-a2be6b09`, `psf-2da1e963`, `psf-07343576`, `psf-b93958e0`, `psf-73058c44` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 4: The main folder keeps flipping to 'bare'

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-4f4f4f97` | **LIVE** | `grep -c core.bare` → `scripts/divineos_push.sh` 0; `scripts/check_push_readiness.sh` 2 (a long comment diagnosing the intermittent `core.bare=true` corruption); `scripts/ready_pr.sh` 5. The push wrapper does not record or restore the setting. | none for the wrapper | The other scripts guard it for their own runs; the row asks for the wrapper. |
| `psf-5693a830`, `psf-c6930351`, `psf-7d82026d` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 5: Counting branches wrongly

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-280ff52a`, `psf-65e65e87` | **UNKNOWN** | `scripts/count_unproposed_branches.sh`, `scripts/branch_triage.py` and `scripts/check_branch_freshness.sh` exist. I did not read whether any asks GitHub directly or names local ghost branches. (The inventory I wrote in round four is a document, not a command.) | none |  |
| `psf-f636e2ae`, `psf-e5836106` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 6: The live house is behind main or holds work main has never seen

8 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-9d0609c8` | **STALE** | `src/divineos/core/upstream_freshness.py:1-30`: at briefing time it fetches origin/main and emits a block when the local main is behind, with the count (called from `knowledge_commands.py` and `surface_bridge.py`). Partly met: it measures the local `main` ref, not whichever branch the live checkout sits on, and it is a prompt, not a block. | none found for the surface | I did not run the briefing to see the block. |
| `psf-234cdf70`, `psf-1d41ad5c` | **LIVE** | The same module's header says: 'Does not auto-pull', 'Does not block. Recognition prompt'. So nothing refuses new work when far behind, and nothing pulls main after a merge. | none | A different file could do it; I looked at the module the briefing uses. |
| `psf-165456e2`, `psf-0e170adc`, `psf-08bb0502`, `psf-f1637b13`, `psf-2a609c04` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 7: Working from a stale local copy

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-0202b5aa`, `psf-db976e05` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

