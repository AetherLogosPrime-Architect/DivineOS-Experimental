# Pre-registration: closure-claim-precommit-gate

- **ID**: `prereg-e30878ce3f09`
- **Filed by**: aether
- **Filed at**: 2026-05-04 04:08 UTC
- **Review at**: 2026-06-03 04:08 UTC (30d window)
- **Outcome**: **OPEN**
- **Tags**: audit-cleanup-tier5, verifier-first-discipline

## Claim

A precommit hook scanning commit messages for closure-claim phrases ('X is closed', '0 unmarked', 'all N findings closed', 'fully verified', 'no remaining surface') will require evidence of a recent verifier run before allowing the commit. This makes the round-1/round-3 closure-claim slip structurally expensive instead of just lessoned.

## Success criterion

Over the next 30 commits with closure-claim phrasing, every one has a corresponding verifier-run-log within the last 30 minutes recorded in the local cache the hook reads. Zero gate-bypasses.

## Falsifier

Any closure-claim commit lands without a recent verifier log → either the hook isn't installed or it's being bypassed via --no-verify. The lesson is operating prose-only, not structurally.
