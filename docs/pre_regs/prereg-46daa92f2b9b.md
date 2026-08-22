# Pre-registration: Findings ledger reduces audit-rediscovery: over 30 days, a repeat audit against origin/main will find a smaller ratio of already-known findings when it starts by reading docs/OPEN_FINDINGS.md than when it starts cold.

- **ID**: `prereg-46daa92f2b9b`
- **Filed by**: agent
- **Filed at**: 2026-07-10 01:05 UTC
- **Review at**: 2026-08-09 01:05 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Ledger reduces rediscovery vs cold-sweep baseline

## Success criterion

Repeat audit's ratio of already-known findings (present in the ledger with status != OPEN) exceeds 60%; overall audit time to complete falls

## Falsifier

Repeat audit finds most of the same items as the initial audit while the ledger sits stale (findings not marked verified/closed as fixes land), OR ledger drifts from actual state because the auto-verify hook doesn't fire, OR humans stop marking OPEN items and the OPEN list becomes noise-only
