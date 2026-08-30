# Audit round: Will-to-vessel auto-prompt Phase A: emit STRUCTURAL_PROMOTION_QUESTION on rule-shape learn entries; dual-monitor CLI for verification; observation-only never blocks

- **ID**: `round-2f6e1e6e600b`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 17:01 UTC
- **Tier**: WEAK
- **Findings**: 2

## Findings

### Andrew CONFIRMS Phase-A observation-only shape with dual-monitor

- **ID**: `find-a45af48093d6`
- **Actor**: user
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Disclose-not-construct: the auto-prompt observes; the operator verifies output vs ledger actuality. Trust earned, not given. Periodic checks remain even after promotion.

### Will-to-vessel auto-prompt Phase A built with explicit fail-safes

- **ID**: `find-4d2de51ae999`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

core/structural_promotion_check.py: rule-shape regex detection (always X / never Y / must Z / every time / in all cases / the only X is Y); loop-prevention suppresses when entry already names falsifier/test/gate/surface/structural; fail-soft on every code path. CLI integration: knowledge_commands.py emits the question after store_knowledge with try/except; never blocks. Dual-monitor: divineos admin structural-promotion-check reports total fired / with follow-up / without follow-up / unanswered. Filed as a claim with explicit falsifiers per Andrew's epistemic-lifecycle teaching (resonance is signal, not proof; file the falsifier alongside the rule). 14 regression-pin tests including loop-prevention + fail-soft. Phase B (promotion to stronger surfacing) requires Phase A to pass 30d review.

**Resolution**

Verified: src/divineos/core/structural_promotion_check.py exists; CLI integration at src/divineos/cli/knowledge_commands.py:201 (import + call after store_knowledge). The 50% tool confidence was a path-prefix miss: knowledge_commands.py was cited without the src/divineos/cli/ prefix. Phase A complete.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
