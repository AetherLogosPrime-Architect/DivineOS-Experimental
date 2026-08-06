# Audit round: root-cause-audit: post-init-state-inconsistency class. Operations claiming to set up a clean substrate state (init, reset-template) leave briefing-visible state partially-empty until a separate operation fires. Surveyed instances: Finding 25 (active_memory empty after init until refresh_active_memory fires), Finding 17 (admin reset-template leaves residue) — same family. Fix-scope for this round: Finding 25 only (active_memory auto-population on init). Finding 17 needs separate scope because reset-template has different invariants. Class-fix discipline: init operations should leave the substrate in the state the briefing describes; users shouldn't have to know about secondary refresh commands.

- **ID**: `round-2cfc08ea1d5a`
- **Filed by**: aether
- **Filed at**: 2026-05-14 00:08 UTC
- **Tier**: WEAK
- **Findings**: 2

## Findings

### Family-audit Finding 17 partial-remediation. Audited admin reset-template for state-residue. Specific instance identified: reset-template clears the active_memory table (line 112 of _LEDGER_TABLES_TO_CLEAR) and reapplies seed, but never called refresh_active_memory afterward. Post-reset briefing surfaced empty active-memory section even after re-seed — same shape as Finding 25 in init. Fix: added phase [6/6] 'Refreshing active memory' to reset_template that calls active_memory.refresh_active_memory(importance_threshold=0.3). Phase-numbering updated /5 → /6 across all 6 phase labels (Finding 9 family — count-drift in source). Note: Finding 17 may have referred to other residue (e.g. ~/.divineos files outside the checkout, leftover lock files, etc.); Aletheia didn't specify. This commit addresses the active_memory residue specifically. Remaining residue (if any) tracked under Finding 17 for follow-up audit.

- **ID**: `find-54ad5643bf07`
- **Actor**: aether
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Finding 17 — active_memory residue specifically; broader residue tracked

### Family-audit Findings 10 + 25 resolved together (post-init-state-inconsistency class). Empirical discovery: 'divineos init' did NOT load seed.json — neither apply_seed nor refresh_active_memory was called from init. The earlier 'Finding 10 fix' (renaming the stale test) was incomplete; this commit adds the actual seed-load + active-memory-refresh to init. Now: init produces '[+] Seed v2.1.0 applied: 9 core slots, 19 knowledge, 5 lessons' + '[+] Active memory populated' in its output. Both happen fail-soft (missing seed.json or refresh error logs warning but doesn't block init success). 4 regression-pin tests in tests/test_init_loads_seed_and_active_memory.py + the renamed test_knowledge_after_init_loads_seed pass. Closes Finding 25 entirely and completes Finding 10 (renamed test now backed by real seed-loading).

- **ID**: `find-a032fe098b00`
- **Actor**: aether
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Findings 10 + 25 — init now actually seeds + refreshes active_memory


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
