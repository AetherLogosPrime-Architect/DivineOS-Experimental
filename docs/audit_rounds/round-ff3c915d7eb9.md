# Audit round: is_fresh() load-bearing bypass — Aletheia's third-hole finding, fix + test

- **ID**: `round-ff3c915d7eb9`
- **Filed by**: aether
- **Filed at**: 2026-07-13 19:45 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: 581615694f6d5a1f1ac4ff9bc5ca1156af4a485b


## Findings

### CONFIRMS: is_fresh() load_bearing bypass + hook holes + template register split — all four fixes verified and approved

- **ID**: `find-be610f1edfbe`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 8565a67f-63bc-40fa-93c8-6d5c2f288071

**Description**

Andrew CONFIRM in-session 2026-07-13 on all four fixes: (1) is_fresh() load_bearing kwarg (guardrail file src/divineos/core/briefing_id.py), (2) hook Finding 1 python-dep in deny path, (3) hook Finding 2 IS_ALETHEIA fail-open on parse miss, (4) family-member-template register split. Explicit quote: 'yes i confirm to all.' Composes with Aletheia's CONFIRM from origin (letter: aletheia-to-aether-2026-07-13-CONFIRM-four-fixes-verified.md). Two independent CONFIRMs on record; round ready to close and PR to main.

### is_fresh() bypass — freshness fast-path hides compaction inside window

- **ID**: `find-76a1cdfc0dda`
- **Actor**: aletheia
- **Severity**: HIGH
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED
- **Routed to**: e311a113-3763-4b1f-a7f4-9f5006da761f

**Description**

is_fresh() reads verified_at_tool from disk and current_tool_count from the ledger. A compaction inside the freshness window touches neither, so is_fresh returns True and the ID-recall challenge (the only compaction-detecting instrument in the system) never fires. Fix: load_bearing kwarg. Callers firing on load-bearing acts pass load_bearing=True and the fast-path is bypassed unconditionally. Toll Booth mapping — ID recall is the toll, fast-path is the coupon that only counterfeit-me would need. Aletheia's letter: family/letters/aletheia-to-aether-2026-07-13-is-fresh-bypass-the-third-hole.md

**Resolution**

CONFIRMED by Aletheia from origin (letter: aletheia-to-aether-2026-07-13-CONFIRM-four-fixes-verified.md) with two independent checks per fix. CONFIRMED by Andrew in-session 2026-07-13. Fix (load_bearing kwarg in is_fresh) + hook-hole fixes + actual-deny-fires tests all verified. Round-ff3c915d7eb9 ready to close and PR to main.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
