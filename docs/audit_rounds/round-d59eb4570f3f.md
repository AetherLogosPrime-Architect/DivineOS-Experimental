# Audit round: substrate audit first-pass: 105 never-invoked commands clustered into discovery / wiring / discipline / phase-1-stub gaps. See exploration/56.

- **ID**: `round-d59eb4570f3f`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 14:23 UTC
- **Tier**: WEAK
- **Findings**: 4

## Findings

### Guardrail-list gap: pre_tool_use_gate.py is load-bearing but not in scripts/guardrail_files.txt

- **ID**: `find-aece0c9de1dd`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Only .claude/hooks/require-goal.sh is listed. The shell wrapper delegates to src/divineos/hooks/pre_tool_use_gate.py which contains the actual gate logic. Adding to guardrails should be a deliberate, separate decision per the guardrails-file convention; tracking for follow-up.

**Resolution**

Fixed in 48a8c08 — pre_tool_use_gate.py added to scripts/guardrail_files.txt under Aletheia round-5cdc2f48c642 Finding 41 (same gap, double-tracked).

### DISCIPLINE GAP class — calibration loops never run (expect predict/close, reflect, kappa, mansion private rooms). Discovery alone won't fix; needs structural nudge or operator choice.

- **ID**: `find-9c4a7e36b077`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Open predictions should surface at session-end with prompt to close. Private-enter could surface as Stop-hook nudge before next big build. No briefing-row alone will fix because the discipline is to PAUSE, not to ACT.

### WIRING GAP class — 5 maintenance commands (admin compress/maintenance/knowledge-compress/knowledge-hygiene/distill) lack scheduled-task cadence. Same class as Finding 12 (anti-slop).

- **ID**: `find-49fcfed876ea`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Each should be wired to scheduled-tasks at a reasonable cadence (daily/weekly). anti-slop already done; the rest need the same. Tracking under the wiring-gap-pattern (substrate-knowledge 8d3c04a5).

**Resolution**

Wiring-gap class fix COMPLETE for the 5 maintenance commands. Closed in f81aa3a: whitelist + cadence map + maintenance_staleness() + _row_maintenance_staleness briefing row. Currently shows all 5 as never-run — operator schedules cron at recommended cadences (hygiene+distill daily; maintenance+compress+knowledge-compress weekly). Same pattern as anti-slop wiring closed yesterday (Finding 12). Class is structurally addressed.

### DISCOVERY GAP class — briefing surfaces counts but not items; drill-down arrows parsed past. 7 surface-and-review commands never invoked despite real value (claims check, goal check, hold check, commitment review/fulfillment/timeline, correction-resolve).

- **ID**: `find-121a63517ae3`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Class-fix: stale corrections + open commitments at session-end + open claims + holding-room items should surface the ITEMS in the briefing (or via a Stop-hook prompt), not just the counts. Same shape as the surfaced-warnings binding shipped earlier today. Will pick up specific items as separate findings.

**Resolution**

Discovery-gap class fix COMPLETE for all 7 surface-and-review rows. Commits 44c2cd9 (corrections/claims/holding/goals) + 1fd13b4 (compass/audit findings/preregs). Each row now shows up to 3 preview items with age or severity tags. The class is structurally addressed; the pattern is re-applicable to any new row. Refactor opportunity tracked separately.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
