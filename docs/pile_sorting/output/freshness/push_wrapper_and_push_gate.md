# Is the note still true? The push step and what it tells me

*Round eight, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (the working copy or a scratch copy of it); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is a habit, an incident record or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: a post office. The wrapper now stamps every parcel with a verdict and writes the verdict down, which answers the oldest complaint. What is still missing is small and concrete: the long-form branch name, tag-only pushes, the reason for a refusal in the last line, and what to do with no branch given.

## Problem 1: I reported a push as landed, refused or in-flight when it was not

9 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-d61f95a5`, `psf-b767feb6` | **STALE** | `scripts/divineos_push.sh`: exits with the push's own code (`exit "$PUSH_EC"`, line 173) and prints `[divineos-push] result: exit=N (...)` as its last line; it also writes the verdict to `push_verdict.txt`, truncated at the start of each run (lines 61-84). Ran on main: `tests/test_a_push_verdict_cannot_outlive_the_truth.py` and `tests/test_the_push_wrapper_reads_both_halves_of_a_refspec.py` → 9 passed. | those two files (9 passed) | That the wrapper is used is a habit; a doorman for background pushes exists (see problem 4). |
| `psf-03762123` | **UNKNOWN** | A wrapper cannot see the command line it sits in. Round six showed the pipe hook refuses a mutating pipe (`git push origin x | tail -2` → DENY). I did not probe `bash scripts/divineos_push.sh … ; echo done`. | none |  |
| `psf-355da87f`, `psf-89a234f4`, `psf-ab38e32a`, `psf-a2a3cb38`, `psf-a614477b`, `psf-5ea6fe01` | **NOT TESTABLE** | An incident record of something I said or did. No run can check it. The structures that answer it exist: the persisted verdict file above and the hook `unlanded-push-must-not-close-quiet.sh`. | none |  |

## Problem 2: The push gate blocks wrongly, or tests the wrong tree

5 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-b0464382`, `psf-0d93e426`, `psf-7a2729f5`, `psf-9c6c56b0`, `psf-66ce3094` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 3: The push helper fails silently for some branch spellings

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-cb3017c7`, `psf-e54da291`, `psf-8caccd2a` | **LIVE** | PR #604 reproduction re-run on current main, **forced** (`--runxfail`): `bash scripts/divineos_push.sh origin HEAD:refs/heads/landing-branch` → the push lands, then the wrapper prints `result: exit=22 (PUSH_FAILED_silently — remote ref missing)` and `remote ref refs/heads/refs/heads/landing-branch not found after push`. Controls pass: the short form `HEAD:landing-branch` is reported as landed. | PR #604 (draft): 1 expected failure, 2 controls | Local bare remote only. |

## Problem 4: The push check cannot find a folder change inside the command, or lets a bare push through

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-bf786823` | **UNKNOWN** | `.claude/hooks/push-message-carries-the-destination.sh` is a doorman that requires a *background* push to use the wrapper (header, 2026-09-10). It refuses; it does not rewrite. I did not probe a foreground bare push. | none found |  |
| `psf-44dcf671` | **NOT TESTABLE** | A habit (what my first-reach push command is). The doorman above is the structure. | none |  |
| `psf-905137db` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 5: The push is refused for memory and gives no help

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c052b2e3` | **LIVE** | `scripts/divineos_push.sh:160-166` prints 'refused for memory, not for readiness. Waiting 60s' and `scripts/check_push_readiness.sh:466` prints '… free memory before retrying'. Neither message lists what is using the memory (the lines I read name thresholds only). | none | I read the lines that print the refusal, not the whole 500-line script. |

## Problem 6: A push that only saves reruns every test; a push that shares reruns tests already passed

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-86fdee3e`, `psf-d2fecc09` | **LIVE** | `grep -n -iE 'save-only|saving push|push.for.sharing|--share|green result' scripts/check_push_readiness.sh .claude/hooks/check-branch-on-push.sh` → no match. Control: the same files hold the deletion-only carve-out (below), so the grep reaches them. | none | A name search. |

## Problem 7: Tag-only and deletion-only pushes

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-05af872b` | **STALE** | `scripts/check_push_readiness.sh:62-69`: 'Deletion-only push detection … If EVERY pushed ref is a deletion' the full gate is skipped; a deletion beside a real ref-update still runs it. | none found for the carve-out | I read the comment and the variable, not a run. |
| `psf-68606fad` | **LIVE** | `grep -n -iE 'refs/tags|--tags|tag-only' .claude/hooks/check-branch-on-push.sh scripts/check_push_readiness.sh` → no match. Control: the same files match 'deletion' (above). | none | A name search. |

## Problem 8: Pushing outside the build flow

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-a7e7d4f8` | **LIVE** | `grep -n -iE 'build.flow|station' scripts/divineos_push.sh` → no match. Control: the same file matches 'verdict' and 'ls-remote', so the grep reaches it. | none | A check elsewhere (a hook) could refuse a push outside the flow; I looked at the wrapper only. |

## Problem 9: Failures not shown with their own evidence

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-8db512f9` | **LIVE** | `scripts/divineos_push.sh:169-173`: on a refused push the last lines are `result: exit=N (PUSH_FAILED)` and a verdict saying 'the gate said no; its reason is in the run output'. The reason itself is not repeated in the final lines. | none |  |
| `psf-ed3856c3`, `psf-36bd1e10` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 10: Rows owed before a push (baseline entries) and wrapper defaults

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-e00a05b3` | **LIVE** | `scripts/divineos_push.sh:184`: with no branch argument the wrapper reports `PUSHED+UNVERIFIED exit=0 -- no branch argument, so this wrapper could not confirm the remote moved`. It does not default to verifying the current branch. | none |  |
| `psf-af66b2cf` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

