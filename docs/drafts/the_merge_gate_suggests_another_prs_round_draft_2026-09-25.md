# The merge gate suggests another PR's round — station one draft, 2026-09-25

**Aria.** The idea, not a plan. Found while merging #556 with Andrew's confirm. Searched first: no draft covers this, and `docs/audit_rounds/round-f97fa965d232.md` records a cousin, `stamp-ready` resolving a round from a branch without checking the confirmed tree.

## What happened

`gh pr merge 556 --squash --body-file ...` was refused by `pr_merge_gate`, correctly, because it reads the trailer from the command text and `--body-file` hides it. Then the refusal offered a ready-to-paste body:

```
PR #545 the doorman holds without its library (...)
External-Review: round-e7999198c141 tree-hash:331dd5c78fa9...
```

That was for **#556**. The round is #545's, and the tree-hash is the tree of the branch my shell happened to be on (`salvage/letters-from-the-four-2026-09-22`), not #556's (`970aaa08...`). Pasting it would have put #556 on main under another PR's review with a third branch's fingerprint. The CI trailer check verifies only that the string is present, so it would have passed. I used #556's own round, `round-f36aaccef6eb`, and the merge landed as `3ac1eafc`.

## Why, in the code

`_find_usable_audit_round(pr_number)` in `core/pr_merge_gate.py` walks `list_rounds(limit=50)` and returns the **first** round that has a user CONFIRMS and an external-AI CONFIRMS within 14 days. `pr_number` is never compared to anything. It only builds a fallback focus string. `_current_head_tree_hash()` reads the local `HEAD^{tree}`, meaning whatever checkout runs the command.

So the helpful path is right only when exactly one confirmed round exists. There were three, filed within minutes of each other.

## The shape

- A round is usable for PR N only if its focus or notes name `#N` or the PR's head branch, the same way build-flow station eight matches rounds. No match means no suggestion, and the long-form instructions instead.
- The suggested trailer carries the round id only, which is the current form per `prepare-merge`'s own 2026-06-18 note. Or it uses a tree read from the PR's head (`gh pr view --json headRefOid`), never from local HEAD.
- The gate reads `--body` text but not `--body-file`, so the safer way to pass a multi-line body is the one it can't see. It should read the named file, or say plainly that it needs `--body`.

## Pin

Three confirmed rounds for three PRs. Asking for PR #556 must return #556's round or nothing, never the newest.

The gate is Aether's (#185, #192, #437), so the shape goes to him.
