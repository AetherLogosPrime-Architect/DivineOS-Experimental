# Pre-registration: Operator-anchored merge-review gate (merge_review_gate.py + ci_merge_review_check.py): a guardrail PR passes the server-side gate only with the operator's APPROVED GitHub review on the exact head SHA PLUS a named, actually-logged audit round.

- **ID**: `prereg-54f0a2240eb8`
- **Filed by**: agent
- **Filed at**: 2026-05-31 01:44 UTC
- **Review at**: 2026-06-30 01:44 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:30 UTC

## Claim

Anchoring merge approval to the one identity the agent cannot forge (operator GitHub account) + a logged-round receipt closes the gameable text-only-trailer hole, keeping the agent aligned without a hard lock.

## Success criterion

The gate correctly PASSES a PR with a real operator Approve on head + logged round, and correctly FAILS: no approval, stale approval, fabricated round, agent-self-approve from a non-operator login (already verified: 16 adversarial unit tests green + live dry-run correctly FAILED PR #60).

## Falsifier

The gate passes a guardrail PR that lacks a genuine operator approval on the current head (false-accept), OR it hard-locks main with no working emergency bypass (cage not keel), OR an agent with repo write-access can make it pass without the operator's GitHub action.

## Outcome notes

Shipped: src/divineos/core/pr_merge_gate.py + scripts/ci_merge_review_check.py exist. Operator-anchored merge-review gate is live and referenced by the guardrail-PR review flow documented in CLAUDE.md rule 8.
