# The merge gate refuses a merge that is behind main

**Written:** 2026-10-18, night. **Branch (to be):** `aether/merge-gate-refuses-a-behind-merge`.

## Why this exists

Aletheia, 2026-10-18, on the stamp retirement (#691): the stamp's refusal of a branch that is behind main was, without anyone having said so, the only thing stopping a behind branch from merging on checks that ran against an older main. I claimed GitHub's own rule covered it. I measured, and it does not: the ruleset "main protection" requires `multi-party-review`, `test (3.12)` and `test (3.12, sklearn)` but has `strict_required_status_checks_policy: false`, so GitHub does not require a branch to be up to date before merging. Her condition, in her words: land #691 only once one replacement is in place. The two replacements she named are this refusal (mine to build) or Dad switching the strict policy on (his call). Either is enough.

## What it does

`gh pr merge N` is already refused by `core/pr_merge_gate.py` when the PR touches a guardrail file and the command has no review trailer. This adds a second, separate refusal that applies to every merge: if the PR's head does not contain main's tip, the merge is refused with the remedy. GitHub's compare endpoint answers it (`behind_by` for `main...<head>`), and the remedy is `gh pr update-branch N`, which merges main into the PR branch on GitHub's servers and reruns the required checks there, so it costs no local test suite and no new signature (the stamp's content rung follows the change, not the floor).

"Behind main by any amount" is the safe stand-in for Aletheia's "checks ran against a different main", not the same question: if the head already contains main's tip the check saw the latest main, and if it is behind the check may still have run on a newer one, so the gate can refuse a merge that would have been fine. That error costs one `update-branch` and a rerun and runs in the safe direction; the exact question would need a guess about timestamps, which is worse.

Three states, kept apart on purpose: fresh (merge may proceed), behind (refused, remedy named), could-not-look (refused, saying so, because an unreadable check must not read as a pass; a merge needs the network anyway).

## Where it lives

A small new module, `core/merge_freshness.py`, holds the reading and the wording. It is a sibling surface in the router (`pr_merge_freshness_surface` in `hook_surfaces.py`, registered beside `pr_merge_gate_surface`), and `pr_merge_gate.py` is not touched at all. CORRECTED 2026-10-18 on Aria's cold read: this paragraph first said `pr_merge_gate.block_reason` gets one call into the module, which the diff never did. The only file the change shares with other open work is `hook_surfaces.py` (one new function and one registration line), and Aria checked that none of her open branches edit it.

## What it does not do

It does not run `update-branch` for me (that is the automation a later doorman could add; per Dad's rule a gate-fire is a finding, not a save). It does not prove the merged result is green: after `update-branch` the checks rerun and the gate asks again at merge. And if main moves again in between, it refuses again; that costs a rerun, never a signature.

WHICH MERGES IT SEES. Aria tried twelve shapes and found the first version asked only when the number came straight after `merge`, so `gh pr merge --squash 42`, the most ordinary way to type it, went ungated. It now reads the pull request as whatever `gh pr view` accepts: a number, `#number`, a URL, a branch name, or nothing at all (which `gh` reads as the pull request of the checked-out branch), with flags allowed before it and the flags that take a value skipped together with their value. Every merge in a chained command is read, not just the first: probing the parser for the walk showed `gh pr merge 1 && gh pr merge 2` asked only about the first, so a stale second PR would have ridden behind a fresh one (the existing merge gate beside it takes only the first match as well). A repository named with `-R` or `--repo` (before or after the pull request, or as `--repo=name`) is read and passed to both GitHub calls, instead of being mistaken for the pull request (Aria's second read of #692). Values of flags that take one are skipped even when quoted, because the quote-scrubber leaves a blank placeholder token in their place, which was checked rather than assumed. What it still does not see is a merge from the web page's button, which is outside every local gate, and a merge made from a folder that is not the repository. The existing merge gate beside it has the old number-first pattern and so has the same hole for its review check; that is a separate finding, below. Measured against real GitHub on 2026-10-18, not just a stand-in: #691 read as 0 behind, #659 as 3 and #592 as 50, and plain `git rev-list --count` agreed on the two it could reach (3 and 0). A merge costs about 1.3 seconds for the two `gh` calls; a command that is not a merge costs nothing.

## Does a review survive `update-branch`? (Aria's cold read, 2026-10-18)

The remedy sentence said a stamped PR's review "still holds" after `update-branch` and nothing pinned it. What is shown, and what is not:

- **From the code.** `scripts/ci_check_guardrail_trailer.sh` reads the trailer from the PR body and, on that path, blanks the tree-hash ("describes the PR, not this commit; not verified here"), so a new head does not break the required check `multi-party-review`. `scripts/ci_merge_review_check.py` (the `merge-review` job, not one of the three the ruleset requires) exits 0 for PENDING, meaning "nobody has approved the current head yet", which is the state of every freshly pushed head; its header says that making it fail was measured to make it unpassable.
- **From real PRs today.** #673, #674, #678 and #681 each had their head moved (a merge of main) after Aletheia's confirm was given, were stamped on the later head by the content rung, and merged with all required checks green. A merge of main into the branch is exactly the commit `update-branch` makes.
- **Not shown.** A literal `gh pr update-branch` on a stamped PR followed by its merge. The first real use will be that case, and this note names it so it is watched, not assumed: if the required checks or the merge-review job refuse a stamped PR after `update-branch`, the remedy this gate names is wrong and the gate must change.

## How we would know it failed

A behind PR merges, or a fresh PR is refused, or a stamped PR that was brought up to date with `update-branch` is refused by a review check. The first is the thing this exists to stop; the others mean the reading or the remedy is wrong.
