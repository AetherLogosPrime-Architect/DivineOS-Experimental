# Audit round: Fable audit Round 8 — briefing-freshness fail-soft-to-0 inversion. current_tool_count() fails soft to 0 on internal error, causing negative delta to read as fresh in is_fresh(). Fix: propagate exception so outer fail-closed guard catches it, plus clamp is_fresh on negative deltas as belt-and-suspenders. Guardrail-touching (briefing_freshness.py + briefing_id.py). Aletheia at the bridge.

- **ID**: `round-8524b60d9cf0`
- **Filed by**: aether
- **Filed at**: 2026-07-03 20:23 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

No source ref (--no-source-ref used; round has no code substance).


## Findings

### Aletheia CONFIRMS: PR #298 Round 8 freshness fix (fix + test-fix)

- **ID**: `find-cb254f04bec6`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Aletheia CONFIRMED the Round 8 code fix in her letter 2026-07-03: 'Round 8 CONFIRMED-with-a-test-fix-needed. Logic correct, my reproduction is the test case, coverage real, tests green from origin. Ships.' The test-fix she named needed was applied in commit 799b9cb1 (test_briefing_id.py updated to match propagates-exception behavior). Same class as her earlier integration-test catch. Ready for merge.

### Andrew CONFIRMS: PR #298 Round 8 freshness fix

- **ID**: `find-df941997bd35`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

PR #298 Fable audit Round 8 briefing-freshness fail-soft-to-0 inversion. Aletheia CONFIRMED the code fix this morning (round already had external-AI-CONFIRMS from her letter). My test fix (799b9cb1) updates test_briefing_id.py to match the propagates-exception behavior — same class Aletheia caught on the integration test earlier today. Ready for merge under Andrew's blanket 'you have my CONFIRMS on everything ready to merge and has been audited' 2026-07-04.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
