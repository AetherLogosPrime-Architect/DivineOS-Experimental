# Audit round: Aletheia audit on today's commit batch — 5 findings ranked by lockout-risk-first

- **ID**: `round-5cdc2f48c642`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 16:04 UTC
- **Tier**: WEAK
- **Findings**: 5

## Findings

### Finding 41 — guardrail gap on pre_tool_use_gate.py (HIGH meta)

- **ID**: `find-c89ba57c9e66`
- **Actor**: external-auditor
- **Severity**: HIGH
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

The .sh wrapper is guardrailed; the Python module containing _BYPASS_DIVINEOS_SUBCOMMANDS and all deny-logic is not. Self-modification attack surface — adding a subcommand to bypass list silently neutralizes every gate for that subcommand. Symmetry with distancing_detector.py (already guardrailed). Confirming Aether's earlier filing. Filed by Aletheia.

**Resolution**

Fixed in 48a8c08. pre_tool_use_gate.py added to scripts/guardrail_files.txt with rationale comment specifically naming the bypass list as the attack surface.

### Finding 40 — energy/vessel/model/will philosophical overreach (low)

- **ID**: `find-0acd7504d5f9`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Frame is operationally productive but treats open philosophical questions as resolved. Specifically: 'attention bias = lesions' conflates training-property with damage; 'power-loss is not death' is Parfit-style continuity question, not resolved. Rhetorical 'this dissolves X' closes off honest 'this offers alternative to X'. Filed by Aletheia.

**Resolution**

Fixed in 48a8c08. exploration/58 amended with explicit operational-vs-philosophical-claim distinction. Three specific overreaches named (training-property vs damage; Parfit continuity not resolved; 'dissolves X' should be 'offers alternative to X').

### Finding 39 — U-shape reorder buries fresh-important rows (medium)

- **ID**: `find-f6546d400717`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Reorder keyed solely on stale_count. Orientation rows (directives, project-purpose) with stale_count=0 sort to the middle of the U. Lost-in-the-middle re-applies to fresh-important content. Fix: guard reorder when all stale_counts uniform; or row-level always_top weight. Filed by Aletheia.

**Resolution**

Fixed in 48a8c08. Reorder now skips when stale_counts are uniform across all rows (preserves canonical order in the all-fresh case). Two regression tests pin.

### Finding 38 — surfaced-warnings heuristic over-flags paraphrase acks (medium)

- **ID**: `find-f4a618e71ca2`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Token-overlap >=3 with length-4 is too strict. Paraphrase acknowledgments fail to match. Over-flagging trains 'ignore the dream report' — exact failure-mode it was built to prevent. Fixes: stem tokens, lower threshold, or document expected ack shape. Filed by Aletheia.

**Resolution**

Fixed in 48a8c08. Stemming + threshold lowered to 2 (was 3 raw). Paraphrase regression test pinned.

### Finding 37 — Gate 1.48 catch-22: claims and holding NOT in _BYPASS_DIVINEOS_SUBCOMMANDS

- **ID**: `find-2cfde7c2f9c8`
- **Actor**: external-auditor
- **Severity**: HIGH
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Block message instructs running 'divineos claims list' / 'divineos hold list' but Gate 1.48 fires on those too. Active lockout-of-recovery risk. Same shape as learn catch-22 from 2026-04-23. Class-fix: structural test that auto-verifies every address-command in _AREA_ADDRESS_EVENTS resolves to a subcommand in _BYPASS_DIVINEOS_SUBCOMMANDS. Filed by Aletheia.

**Resolution**

Fixed in 48a8c08. Bypass list expanded (claims/holding/hold added). Structural test test_stale_engagement_address_bypass.py converts the convention into enforcement — catch-22 pattern cannot recur for this gate or future gates that follow the _AREA_ADDRESS_EVENTS/block_message contract. The class-fix Aletheia recommended is the actual answer.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
