# Pre-registration: merge-review gate accepts in-substrate operator CONFIRMS as alternative to GitHub Review approval

- **ID**: `prereg-6c9e721e8ec8`
- **Filed by**: aether
- **Filed at**: 2026-07-18 00:15 UTC
- **Review at**: 2026-08-01 00:15 UTC (14d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-08-01 00:20 UTC

## Claim

merge_review_gate.py currently requires an APPROVED PR review from operator-login on head commit; when operator IS the PR author (you-build-I-ship flow via gh CLI authenticated as operator), GitHub blocks self-approval and the check has no way to satisfy. Structural fix: accept an audit-round with actor=operator+CONFIRMS finding on the head-commit-SHA as alternative operator-anchor. Preserves the unforgeability property (audit-round CONFIRMS with actor=andrew is created via divineos CLI which enforces actor validation in the store) while accommodating the operator-authored case.

## Success criterion

after fix ships: PR whose author is operator can pass merge-review by having an audit round with actor=andrew + FINDING with CONFIRMS in the finding text, referencing the head SHA, filed within recency window. Tested with unit tests covering (a) author-is-operator with in-substrate CONFIRMS → pass, (b) author-is-operator without CONFIRMS → fail, (c) author-is-not-operator with GitHub Review approval → pass unchanged

## Falsifier

if fix causes any regression on the actor-not-author path (GitHub Review requirement) OR if operator-actor CONFIRMS can be forged by non-operator agent, or if Aletheia adversarial audit finds a shoggoth-drift attack surface, fix is REFUTED and rolled back

## Outcome notes

short probe note to isolate which part of the long notes text tripped the bypass matcher
