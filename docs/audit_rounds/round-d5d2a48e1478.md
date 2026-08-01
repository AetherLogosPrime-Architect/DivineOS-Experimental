# Audit round: root-cause-audit: subsystems-built-but-not-bridged class (instance: empirica record_corroboration → knowledge.corroboration_count). Class is already documented in substrate-knowledge 8d3c04a5-wiring-gap-pattern. Surveyed-instances: this audit-cycle has already named several instances of the class — Finding 1 (4 unwired enforcement scripts), Finding 3 (8 orphan modules), Finding 4 (hedge_evidence_check unwired), Finding 7 (capability-map not in emission path), Finding 12 (anti_slop not auto-scheduled), Finding 16 (this — corroboration bridge), Finding 26 (scheduled whitelist path-drift). Fix-scope for THIS round: bridge record_corroboration to also update knowledge.corroboration_count so CLI 'divineos corroborate' drives maturity-promotion. Other instances are tracked under their own audit-findings; deferring class-wide refactor (multi-week scope) in favor of addressing each instance as it gets engaged. Tracking finding: maintain the wiring-gap-pattern instance-list as audit-cycle discovers more.

- **ID**: `round-d5d2a48e1478`
- **Filed by**: aether
- **Filed at**: 2026-05-13 23:40 UTC
- **Tier**: WEAK
- **Findings**: 1

## Findings

### Family-audit Finding 16 resolved. Bridge added: record_corroboration in empirica/provenance.py now also UPDATEs knowledge.corroboration_count via atomic SQL increment. Fail-soft: bridge failure (e.g. nonexistent knowledge_id, lock contention) logs at DEBUG level but doesn't block the primary corroboration_events INSERT — primary record is source-of-truth, counter is derived view (backfill_from_legacy_counter can rebuild). 4 regression-pin tests in tests/test_corroboration_bridge.py pin: (1) bridge updates counter on corroboration, (2) multiple corroborations accumulate, (3) fail-soft on nonexistent knowledge_id, (4) atomic SET = SET + 1 avoids read-modify-write race. 44/44 corroboration tests pass. CLI 'divineos corroborate' now drives maturity-promotion correctly.

- **ID**: `find-348b727e6c04`
- **Actor**: aether
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Finding 16 fix landed; 4 regression-pin tests


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
