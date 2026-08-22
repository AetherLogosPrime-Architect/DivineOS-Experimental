# Pre-registration: Bypass-list mirror sync-test — assert CLI _BYPASS_COMMANDS and scripts/hook_bypass_commands.txt agree on what's allowed through the safety layer

- **ID**: `prereg-a49e649f5a26`
- **Filed by**: agent
- **Filed at**: 2026-07-17 17:35 UTC
- **Review at**: 2026-08-16 17:35 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Two independent bypass lists (CLI-layer _BYPASS_COMMANDS in src/divineos/cli/__init__.py + hook-layer scripts/hook_bypass_commands.txt) must stay in sync or one gate's bypass creates the other gate's deadlock (F22/F31 family + PR #356 goal-add deadlock). Mechanism: add a test tests/test_bypass_list_mirror.py that parses both files' bypass lists and asserts symmetric membership OR names any allowed asymmetry with rationale. Test runs in the standard suite so drift fails CI, preventing another goal-add-style deadlock.

## Success criterion

Over 30 days: (a) no new bypass-list drift bug lands (test would have caught PR #356's original state), (b) the test itself doesn't need >1 rebase-fix per month (stability), (c) any legitimate asymmetry between the lists is explicitly documented in the test's allowlist with rationale.

## Falsifier

If in 30 days: (a) any bypass-list drift bug reaches main and the test didn't catch it (either it's mis-scoped or bypassed), OR (b) the test needs >3 rebase-fixes per month (too fragile), OR (c) legitimate asymmetries accumulate in the allowlist without rationale (Goodhart on the test itself), THEN redesign — likely the deeper fix (single source both layers read) is needed.
