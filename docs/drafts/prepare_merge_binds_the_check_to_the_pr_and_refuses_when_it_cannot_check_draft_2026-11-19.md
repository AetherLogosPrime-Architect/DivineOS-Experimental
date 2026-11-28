<!-- tags: prepare-merge, aletheia, hold, pr binding, cannot check, refuse, gh, patch-id -->
# prepare-merge binds the check to the PR GitHub names, and refuses when it cannot check (draft, 2026-11-19)

Author: Aether. Aletheia held #864 at 01282b9a1 (letter aletheia-to-aether-2026-11-19-864-held-three-of-my-four-kicks-got-through): three of her four attacks got merge text for a PR that moved after her yes. Dad carried it. Nothing here is built.

## What got through, and why (her three, read against the code)

1. `--branch typo`: anchor_state_for_round returns cannot-check, and the command prints "This is NOT a pass" and then hands the text over anyway (exit 0). The words said refuse and the code said proceed.
2. A copy branch (`feature-as-she-saw-it`, the reviewed version, untouched) named with `--branch` vouches for the moved PR: the command checks whatever branch the caller names, and nothing says that branch is the PR being merged. A flag the caller can point anywhere is a rule, not a structure.
3. Detached HEAD with no `--branch`: no branch, so cannot-check, same hole as 1.
The fourth, an edit smuggled into a catch-up merge commit, was caught: the patch-id moved.

## The fix

(a) cannot-check refuses, exit 1, nothing handed over, the same as stale. A door that cannot see stays shut. There is no flag to turn it off.
(b) The PR is resolved by GitHub, not named by the caller. New `resolve_pr_head(pr)` asks `gh pr view [N] --json number,headRefName,headRefOid`: with `--pr N` it asks about that PR, without it asks about the current branch's PR (gh does this itself and fails on a detached HEAD, so attack 3 refuses at once). The branch the check runs on is GitHub's headRefName, and `--branch` stays only as an assertion: if given and different from the PR's head, refuse (attack 1 and 2 refuse). gh missing, offline, unauthenticated, or answering with no PR: cannot-check, refuse.
(c) After anchor_state_for_round has fetched, the tip of origin/<head> must equal GitHub's headRefOid. If it does not, the local view is not the PR's version: refuse.
(d) The handed-over text carries one more line, "Reviewed PR #N at <sha>", so the merge text names the PR it was prepared for. This is what the GitHub-side check (her next ask) will compare against the PR body.

## Where it still stops, said before she has to say it

It cannot know which PR the text is pasted into. Someone who prepares for PR A and pastes into PR B is not seen here; only a check on GitHub's side, which knows the PR it is running on, closes that. That check is the next change (patch-id in the PR body, a required status check), and #864 alone does not close it. Also patch-id ignores swapping tabs for spaces, which matters only in a file where whitespace is meaning (a Makefile, YAML) and only on a catch-up where the tree also changed; low priority, named here so it is not lost.

## Tests

Real git as before, with the PR resolver patched (gh is not in a test run). Her four attacks go in as tests, flipped to expect refusal for 1 to 3 and refusal for 4. Added: gh unresolvable refuses; origin tip differing from GitHub's headRefOid refuses; the old cannot-check-hands-over test is rewritten to expect exit 1. The earlier holds and stale tests keep their meaning with the resolver patched to the real branch.

## What would change my mind

gh unavailable on the machine that actually runs prepare-merge (then the door is shut for good and the fix is wrong for this house); or a way for the caller to steer `--pr` to a PR with the reviewed content that I have not thought of (then the walk missed it).
