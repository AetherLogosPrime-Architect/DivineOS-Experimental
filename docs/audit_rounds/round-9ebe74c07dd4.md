# Audit round: Round-18: Aletheia round-17 obs #1 + #2 follow-up. Replaced env-dependent test with exit-1 wrapper. Added behavioral tests for hole-1 (missing lib) and hole-2 (find_python returns non-zero). All 3 holes now have behavioral + structural coverage. tree-hash: 0693d355f487ca3bba6c0c09191651d83bebc261 diff-hash: 321cbb9d8eff27ffd4d4131acd356c1f5c97891969db30aaea4f761cf10841cb

- **ID**: `round-9ebe74c07dd4`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-11 01:11 UTC
- **Tier**: WEAK
- **Findings**: 2

## Findings

### Round-18 user CONFIRMS

- **ID**: `find-d362befd1406`
- **Actor**: user
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Andrew confirmed 2026-05-10 after Aletheia's round-19 CONFIRMS for the round-18 behavioral coverage patch.

**Resolution**

CONFIRMS-recognition event — already resolved at filing time; closing in batch 2026-05-12 dogfood pass. The audit-findings model conflates CONFIRMS (positive verification) with RAISES (open issues); CONFIRMS should not surface as unresolved.

### Round-18 follow-up CONFIRMS — behavioral coverage verified on Linux

- **ID**: `find-82410cf1c730`
- **Actor**: claude-aletheia-auditor
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

Aletheia round-19 empirically verified all three new behavioral test scenarios fire correctly on Linux: missing _lib.sh → deny mentioning lib/source; find_python returns 1 → deny mentioning python/binary; subprocess exits 1 → deny mentioning subprocess/refusing. Behavioral coverage now even across all three holes; env-dependency in test_python_with_no_divineos resolved via exit-1 wrapper. Closes round-17 obs #1 and #2.

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

**Resolution**

CONFIRMS-recognition event — already resolved at filing time; closing in batch 2026-05-12 dogfood pass. The audit-findings model conflates CONFIRMS (positive verification) with RAISES (open issues); CONFIRMS should not surface as unresolved.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
