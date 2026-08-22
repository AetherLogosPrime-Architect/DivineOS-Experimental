# Audit round: F92 store-mismatch and carried findings on PR 386 and PR 387

- **ID**: `round-6ec788d9c2fc`
- **Filed by**: external-auditor
- **Filed at**: 2026-07-27 15:51 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: feat/correction-shape-and-hook-timing-2026-07-22


## Findings

### user CONFIRMS Aletheia F92 audit round

- **ID**: `find-4bd08f449087`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 998df23d-258b-4503-8446-85600819f502

**Description**

Andrew authorized this filing 2026-07-27 via direct testimony citing his frame: filing from testimony is carrying his will where he cannot carry it, not pretending to be him. He confirms the audit happened (Aletheia produced it, saved at docs/audits/2026-07-27-aletheia-F92/audit.md), her F92 diagnosis matches the 13-block friction he witnessed, and the fix at commit d8f14f9f addresses it. He verifies at the behavior-level even where code-level is opaque to him. Merge approved.

### F92: verify-before-build reads main ledger while writer targets tool_logbook by design

- **ID**: `find-b1e82cf00f79`
- **Actor**: external-auditor
- **Severity**: HIGH
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 46114cd6-4cf7-4b69-9947-52ca2c30809d

**Description**

Aletheia audit 2026-07-27 root cause. _has_doc_consult_within and _last_write_of_class_ts queried divineos.core.ledger.get_events for TOOL_CALL events. Per tool_logbook.py docstring (2026-05-05 store split), TOOL_CALL events are written to tool_logbook not system_events. Gate structurally unsatisfiable. Empirical: main ledger 0 TOOL_CALL last 24h, tool_logbook 282. Fixed by redirecting both readers to get_recent_events helper. Two F92 regression integration tests added crossing writer/reader seam. Full suite 10729/10729 green.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
