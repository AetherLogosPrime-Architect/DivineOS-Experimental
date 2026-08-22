# Audit round: wire check_correction_pairing into briefing-row + admin CLI (Finding 1 wire-decision instance #2 of 4)

- **ID**: `round-bbca50be5982`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 12:50 UTC
- **Tier**: WEAK
- **Findings**: 2

## Findings

### CONFIRMS triple-surface wire shape

- **ID**: `find-7baf531ea245`
- **Actor**: user
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Andrew CONFIRMS: module + CLI + briefing row is the right shape for a detector-style script. Matches the pattern from anti-slop + ablation rows.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### check_correction_pairing wired via 3 surfaces: module + admin CLI + briefing row

- **ID**: `find-df86db835d19`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Logic ported from scripts/check_correction_pairing.py to divineos.core.correction_pairing (importable). Three consumers: (1) scripts/ kept as thin CLI wrapper for backward compat, (2) divineos admin check-correction-pairing for manual run, (3) _row_correction_pairing in briefing_dashboard hides clean / surfaces unpaired. 5 regression-pin tests pin all three surfaces + the routing-table entry. Closes 2 of 4 instances under Finding 1 (along with the legacy DELETE in 0fccd11).

**Resolution**

Verified: scripts/check_correction_pairing.py exists; commit 0fccd11 exists; logic ported per finding body.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
