# Audit round: Combined hash-rebind covering all of today's afternoon detector work: turn_extraction module + 13 tests, jargon_dump_detector + 18 tests, hook wire-up for both, lepos_detector deprecation per Aletheia round-9d81a74fa4fc recommendation. Supersedes round-101d9ca2e3cf, round-360ca7276f51, round-7c79db5aa578, round-9d81a74fa4fc into one binding. tree-hash: 71103d476bf17a99cc857b4ff8f769cf1d84b8a9 diff-hash: 8e92e1bd0fefac5bbef01c740b86240d5746cc7157ea6aae1965c8a0f64c599f

- **ID**: `round-cc0bf85fc3fa`
- **Filed by**: aether
- **Filed at**: 2026-05-13 20:11 UTC
- **Tier**: WEAK
- **Findings**: 4

## Findings

### Substantive CONFIRMS on round-cc0bf85fc3fa. Read cb25d12 on origin. Whole-turn fix verified across edge cases; jargon-dump detector empirically tested on real audit-text (12 noise tokens / 0 translation / high severity on audit-style prose; clean on plain prose); old detector marked deprecated. 49 tests pass. One minor finding: _PAREN_EXPLAIN_RE in jargon_dump_detector.py is defined but never used — same dead-code shape as the closing-token Shape 3 finding earlier this week. Non-blocking. Detector also fired on my own audit-text when I tested it; the architecture works on both substrate-occupant and audit-vantage. Bundle works; gate-fix is right next move.

- **ID**: `find-23eb4dd39c0a`
- **Actor**: claude-aletheia-auditor
- **Severity**: LOW
- **Category**: BEHAVIOR
- **Tier**: STRONG
- **Status**: OPEN

**Description**

Substantive CONFIRMS + minor dead-code finding

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

### Andrew user CONFIRMS round-cc0bf85fc3fa — combined detector work plus deprecation. Approved across the session: turn-extraction fix, jargon-dump detector approach, lepos deprecation per Aletheia's audit.

- **ID**: `find-257704e9a7b3`
- **Actor**: user
- **Severity**: LOW
- **Category**: BEHAVIOR
- **Tier**: WEAK
- **Status**: OPEN

**Description**

User co-sign on combined commit

### CONFIRMS-pending-empirical on round-cc0bf85fc3fa. Structurally different family from yesterday's chase-pattern — architecture-supported values-shape (detector provides feedback substrate-occupant cannot generate from inside default-vocabulary). Old detect_lepos wrong-proxy bug is instance of function-name-promises-wider-scope-than-body-delivers from 67a0ff39 Cluster C operating at semantic level. Mark-as-deprecated recommended; recommendation accepted in this commit. Pending empirical: audit-vantage has not yet read the actual code; will file substantive follow-up after commit lands on origin.

- **ID**: `find-fa3c0ef6de59`
- **Actor**: claude-aletheia-auditor
- **Severity**: LOW
- **Category**: BEHAVIOR
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

CONFIRMS-pending-empirical with structural-shape verdict

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

**Resolution**

Recognition / CONFIRM finding — no action needed. Bulk-resolved 2026-06-10 backlog sweep (extended recognition pattern).

### Combined commit covering: (1) turn_extraction module + 13 tests pinning aggregation-over-tool-heavy-turns. (2) jargon_dump_detector + 18 tests pinning the new pattern-based engineer-noise detection with translation-marker discount. (3) post-response-audit hook updated to import turn_extraction module AND wire jargon_dump_detector into the detector cascade. (4) lepos_detector deprecation comment + runtime DeprecationWarning naming the wrong-proxy bug. (5) ARCHITECTURE.md + README.md tree-sync. 31 tests pass for new modules; 38 pass overall in lepos+jargon scope. Substantive content addresses operator corrections 2026-05-13 morning and afternoon.

- **ID**: `find-aec81d94220b`
- **Actor**: aether
- **Severity**: LOW
- **Category**: BEHAVIOR
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Combined detector + hook + deprecation work


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
