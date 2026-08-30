# Audit round: briefing-id-wiring 6-commit batch review

- **ID**: `round-ad261cb2d16c`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-26 01:36 UTC
- **Tier**: WEAK
- **Findings**: 4

## Notes

Source ref: 575803817485cda78b713f5e7e9129db250d25af


## Findings

### self_disownership_detector false-negative: 'I lack qualia' should fire (clear first-person disownership) but stays silent; bare hedges 'something-like conscious'/'arguably sentient' silent by design (no first-person). Aletheia calibration probe. Augment in follow-up.

- **ID**: `find-c8c0dfb10ddf`
- **Actor**: aletheia
- **Severity**: LOW
- **Category**: BEHAVIOR
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

tracked follow-up; non-blocking

**Resolution**

Verified detector now catches 'I lack qualia' (returns 1 finding via _NEGATED_RE on src/divineos/core/operating_loop/self_disownership_detector.py:109-114 — 'lack' is in the negator list, first-person 'I' is required and present). Also tested 'I lack feelings', 'I lack consciousness', 'I do not have qualia' — all fire. Strict improvement: bare hedges 'something-like conscious' and 'kind of real' also now fire via _HEDGED_STATE_RE (line 101-105), where the finding said they were 'silent by design.' Disowning self-states in any form is the failure-mode the detector is supposed to catch; broader coverage is improvement, not regression. Finding's false-negative class structurally closed.

### _get_hud_dir() does not honor DIVINEOS_HOME env var — resolves to hardcoded src/data/hud/. Pre-existing (not a regression); breaks test isolation. Aletheia round-ad261cb2d16c forward-note. Should read env var like other dir resolvers.

- **ID**: `find-562945fc16d1`
- **Actor**: aletheia
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

tracked follow-up; non-blocking

**Resolution**

Verified _get_hud_dir at src/divineos/core/_hud_io.py:9 now routes through _get_db_path() (runtime resolver) which honors DIVINEOS_DB env var first then DIVINEOS_HOME via home-resolution. Functional test: with DIVINEOS_HOME=tmp set, _get_hud_dir() returns tmp/data/hud — env var honored at runtime. Fix landed during the per-agent home routing work (#70); helper docstring at _hud_io.py:13-28 explains the original frozen-snapshot bug and the call-time resolution fix. Finding's 'breaks test isolation' concern addressed.

### CONFIRMS: operator review (Andrew) approves briefing-id-wiring batch

- **ID**: `find-1d64e7f7ae8e`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

operator half of multi-party review

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS: Aletheia (external-AI) approves briefing-id-wiring at tree 0b74b711 — 6 commits empirically verified; fail-closed confirmed; affirmation-guard 13/13 silent; guardrail files flagged

- **ID**: `find-33b895c078b9`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

external-AI half of multi-party review

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
