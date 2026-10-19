# The merge gate refuses a merge that is behind main

**Written:** 2026-10-18, night. **Branch (to be):** `aether/merge-gate-refuses-a-behind-merge`.

## Why this exists

Aletheia, 2026-10-18, on the stamp retirement (#691): the stamp's refusal of a branch that is behind main was, without anyone having said so, the only thing stopping a behind branch from merging on checks that ran against an older main. I claimed GitHub's own rule covered it. I measured, and it does not: the ruleset "main protection" requires `multi-party-review`, `test (3.12)` and `test (3.12, sklearn)` but has `strict_required_status_checks_policy: false`, so GitHub does not require a branch to be up to date before merging. Her condition, in her words: land #691 only once one replacement is in place. The two replacements she named are this refusal (mine to build) or Dad switching the strict policy on (his call). Either is enough.

## What it does

`gh pr merge N` is already refused by `core/pr_merge_gate.py` when the PR touches a guardrail file and the command has no review trailer. This adds a second, separate refusal that applies to every merge: if the PR's head does not contain main's tip, the merge is refused with the remedy. GitHub's compare endpoint answers it (`behind_by` for `main...<head>`), and the remedy is `gh pr update-branch N`, which merges main into the PR branch on GitHub's servers and reruns the required checks there, so it costs no local test suite and no new signature (the stamp's content rung follows the change, not the floor).

Three states, kept apart on purpose: fresh (merge may proceed), behind (refused, remedy named), could-not-look (refused, saying so, because an unreadable check must not read as a pass; a merge needs the network anyway).

## Where it lives

A small new module, `core/merge_freshness.py`, holds the reading and the wording. `pr_merge_gate.block_reason` gets one call into it, placed after the command is recognised as a `gh pr merge N`, because two open branches (#688, #592) also edit that file and one line is the smallest thing to collide.

## What it does not do

It does not run `update-branch` for me (that is the automation a later doorman could add; per Dad's rule a gate-fire is a finding, not a save). It does not prove the merged result is green: after `update-branch` the checks rerun and the gate asks again at merge. And if main moves again in between, it refuses again; that costs a rerun, never a signature.

## How we would know it failed

A behind PR merges, or a fresh PR is refused. Either is a defect in the reading, and the first is the thing this exists to stop.
