# Audit round: root-cause-audit: default-value-drift-between-entry-points class. Same operation reachable via multiple entry-points (CLI, Python API, ledger event-emission) where each path has its own implicit defaults. Default-drift produces silent inconsistency depending on caller. Instance: Finding 31 — store_knowledge confidence default is 0.5 in CLI, 1.0 in Python API. Class-fix: align defaults at the lowest-trust value (0.5) so forgetful callers don't get max confidence silently. Surveyed-instances: this finding only — other entry-point pairs not yet enumerated; tracking finding for follow-up audit.

- **ID**: `round-335aaeeffc26`
- **Filed by**: aether
- **Filed at**: 2026-05-14 00:37 UTC
- **Tier**: WEAK
- **Findings**: 1

## Findings

### Finding 31 resolved. store_knowledge Python API default confidence changed from 1.0 to 0.5 to match CLI's --confidence default. Both paths now err toward needing more evidence before high-confidence claims rather than silent max-confidence default for forgetful callers. 21 of 25 existing callers pass confidence explicitly and are unaffected; 4 default-relying callers now get 0.5 instead of 1.0 — semantic shift toward less-aggressive maturity-promotion. 295 knowledge tests + 2 new regression-pins pass. Class-fix scope note: only this entry-point pair (CLI vs Python API store_knowledge) audited; other default-drift surfaces tracked for future audit under the default-value-drift-between-entry-points class.

- **ID**: `find-6d060a54a040`
- **Actor**: aether
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Confidence default aligned at 0.5; 295 knowledge tests pass


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
