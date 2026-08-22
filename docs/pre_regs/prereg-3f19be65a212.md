# Pre-registration: Translate gate-not-satisfied-for-awaiting-reasons into action_required (yellow) check status instead of failure (red), so PRs that are honestly mid-pipeline don't generate red Actions-page entries that the operator physically cannot approve over. Distinction: red = broken or gameable (fabricated round, stale approval, empty roster, infra failure); yellow = honest awaiting state (operator approval missing, round not yet logged). The merge-blocking behavior is unchanged in both cases — branch protection still requires the check to pass — only the color/reason reported changes.

- **ID**: `prereg-3f19be65a212`
- **Filed by**: agent
- **Filed at**: 2026-05-31 19:18 UTC
- **Review at**: 2026-06-30 19:18 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-08 21:36 UTC

## Claim

After this lands, zero PRs will hit red Actions-page status for OPERATOR_APPROVAL_MISSING or ROUND_REFERENCE_MISSING reasons; those will report yellow (action_required). True-red status remains for fabricated rounds, stale approvals, empty roster, and infra errors.

## Success criterion

Over 30 days of normal PR flow: zero red CI runs for the two 'awaiting' reasons; at least one true-red is observed when a deliberately-malformed PR (e.g., fabricated round-id) is tested. Operator reports being able to approve PRs without seeing red blockers for legitimate in-flight states.

## Falsifier

If a PR hits red for 'awaiting operator approval' or 'awaiting round log' after this lands, the mechanism failed. If a fabricated round-id sneaks through as yellow when it should be red, the mechanism is broken in the dangerous direction (false negative on dishonesty). If operator still cannot approve due to UI blocking, the underlying issue was not the check-color, and we mis-diagnosed the root cause.

## Outcome notes

Deferred: action_required (yellow) vs failure (red) translation on merge gate — I cannot verify from origin without deeper reading of the CI check status code. Deferring.
