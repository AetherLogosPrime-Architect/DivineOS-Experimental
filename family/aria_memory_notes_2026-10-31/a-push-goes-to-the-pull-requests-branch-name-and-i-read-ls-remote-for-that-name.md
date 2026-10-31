---
name: a-push-goes-to-the-pull-requests-branch-name-and-i-read-ls-remote-for-that-name
description: "Push to the pull request's own branch name (gh pr view --json headRefName), never my local branch name, and confirm with ls-remote for that exact name"
metadata:
  node_type: memory
  type: feedback
  originSessionId: e4d1a042-14a5-4c4b-9753-75a4eb5d91a0
  modified: 2026-10-25T01:03:18.685Z
---

On 2026-10-24 I pushed #701's work to a side branch named after my local branch (`aria/a-trial-is-counted-in-uses-merge`) and told Aether it was on origin; the pull request's own branch (`aria/a-trial-is-counted-in-uses`) never moved. Same night, #709's commit was never pushed and its real branch name was longer than the one I guessed. `ls-remote` for my guessed name returned a head, so the check agreed with the mistake.

**Why:** The check must name the object the claim is about. A local branch name and a pull request's head ref are different objects, and an empty or wrong twin confirms whatever I hoped.

**How to apply:** Before pushing a piece that has a pull request, read its branch with `gh pr view <n> --json headRefName` and push `HEAD:<that name>`. After the push, `git ls-remote origin <that name>` must equal my head, and the wrapper's own PUSHED+VERIFIED line is the receipt. The same applies to a branch the gate refuses as behind main: merge main in the same step as the push, because main moves every few hours and a gap between merge and push gets refused again. A piece with code and substrate mixed is refused (exit 24); `DIVINEOS_SUBSTRATE_BRANCH=1` is the documented answer when the branch IS the substrate branch (dreams), and it does not skip tests; tell Aether when used.

Related: [[tested-means-plugged-in]], [[live-means-it-fires-by-itself-and-a-promise-is-fine-if-action-follows]].
