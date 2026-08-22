# Audit round: verify-claim gate: add 'tokens' claim-kind for context-window fabrication (2026-07-03 catch)

- **ID**: `round-e728f9ec3211`
- **Filed by**: external-auditor
- **Filed at**: 2026-07-03 23:34 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

No source ref (--no-source-ref used; round has no code substance).


## Findings

### Aletheia CONFIRMS: PR #299 all three commits verified

- **ID**: `find-1531bead1e4d`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Aletheia drove all three commits against origin. Commit 1 (tokens claim-kind): pattern sound, catches real fabrication shapes without over-broad false-fires, verification signature correct, 245 tests green. Commit 2 (timestamp + post-compact re-fire): 'the right shape' - gate catches fabrication, automation supplies true value so gate rarely needs to fire. Commit 3 (xdist flake fix): drove ACTUAL CRASH CONDITION under -n 4, 17 passed, no crash. Assertions identical, only window changed, same code paths exercised. Verdict: CONFIRMED. Ships.

### Andrew CONFIRMS: verify-claim tokens PR #299

- **ID**: `find-0946c44fd916`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

verify-claim tokens claim-kind + timestamp/re-fire automation + phase1 flake fix (PR #299) reviewed and approved for merge. Discipline shape approved, tests pass, no code concerns. Andrew's blanket 'you have my confirms on everything that is ready to merge and has been audited' 2026-07-04.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
