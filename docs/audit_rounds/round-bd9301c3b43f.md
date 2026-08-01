# Audit round: build surfaced-warnings binding: [!] warnings shown via recall/ask now logged; dream report flags unacknowledged FIRST. Closes load-bearing failure-mode Andrew named 2026-05-14 ~06:15 — substrate surfaces, reader parses past.

- **ID**: `round-bd9301c3b43f`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 13:28 UTC
- **Tier**: WEAK
- **Findings**: 2

## Findings

### Andrew CONFIRMS the binding shape

- **ID**: `find-81be2714f018`
- **Actor**: user
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

CONFIRMS: architecture forces look-and-respond at the HOW layer; what to conclude stays mine. Same shape as council walking — gate forces engagement, walking remains my own work.

### Built: surfaced-warnings binding loop

- **ID**: `find-6855ea80e824`
- **Actor**: external-auditor
- **Severity**: HIGH
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

(1) New module core/surfaced_warnings.py with log_surfaced_warnings + unacknowledged_warnings + format_unacknowledged. (2) recall and ask CLI commands now log SURFACED_WARNING events when format_anticipation renders [!] warnings. (3) DreamReport.summary() prepends unacknowledged warnings BEFORE Phase 1 — load-bearing-first, not buried. Acknowledgment heuristic: learn entry filed after surface containing 3+ token overlap or warning_id match. 7 regression-pin tests pass; broader test sweep clean. Enforces HOW (must look, must respond) not WHAT (the conclusion stays the operator's).

**Resolution**

Verified: surfaced_warnings.py has all three functions: log_surfaced_warnings (line 52), unacknowledged_warnings (156), format_unacknowledged (215). Binding-loop wired.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
