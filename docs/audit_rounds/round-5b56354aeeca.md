# Audit round: Aletheia round-16 follow-up: cross-platform test portability fix (git init inside fake_repo). tree-hash: 13f6b118cbb4b0dd8773f6e70f1cfd2c497d8515 diff-hash: 2017b2a1b18c46a2fe91dfaa201cdb4f05cb57efbe4f8623439f97a8676282fe

- **ID**: `round-5b56354aeeca`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-11 00:47 UTC
- **Tier**: WEAK
- **Findings**: 2

## Findings

### Round-17 user CONFIRMS

- **ID**: `find-dcd9a8d46501`
- **Actor**: user
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Andrew confirmed in session 2026-05-10 for round-17 commit shipping the round-16 cross-platform test portability fix, with explicit acknowledgment that the two coverage observations from Aletheia will be addressed in round-18 follow-up. tree-hash: 13f6b118cbb4b0dd8773f6e70f1cfd2c497d8515

**Resolution**

CONFIRMS-recognition event — already resolved at filing time; closing in batch 2026-05-12 dogfood pass. The audit-findings model conflates CONFIRMS (positive verification) with RAISES (open issues); CONFIRMS should not surface as unresolved.

### Round-17 CONFIRMS — fix verified empirically on Linux

- **ID**: `find-809792dfda7f`
- **Actor**: claude-aletheia-auditor
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

Aletheia round-17 verified all 3 fail-closed holes operate correctly on Linux after the git init portability fix. Substantive fix correct. Two non-blocking observations for follow-up: (1) Linux env-dependency in test_python_with_no_divineos (PYTHONPATH= insufficient when divineos is pip install -e installed in site-packages); (2) behavioral coverage uneven — only hole-3 has behavioral test, holes 1+2 only structural. Recommendation: merge now, address coverage in small follow-up per smaller-loops discipline. diff-hash: 2017b2a1b18c46a2fe91dfaa201cdb4f05cb57efbe4f8623439f97a8676282fe tree-hash: 13f6b118cbb4b0dd8773f6e70f1cfd2c497d8515

**Resolution**

CONFIRMS-recognition event — already resolved at filing time; closing in batch 2026-05-12 dogfood pass. The audit-findings model conflates CONFIRMS (positive verification) with RAISES (open issues); CONFIRMS should not surface as unresolved.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
