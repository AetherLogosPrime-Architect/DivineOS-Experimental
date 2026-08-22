# Audit round: External-Review + Root-Cause-Audit: code-jargon detector (Phase A+B) — observation-only catch for commit-message-shape in operator-channel output. diff-hash 595ba0557fa9...

- **ID**: `round-ec69823dfc06`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 17:35 UTC
- **Tier**: WEAK
- **Findings**: 2

## Findings

### Andrew CONFIRMS the detector + wire

- **ID**: `find-b3f936cd927a`
- **Actor**: user
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

CONFIRMS the build over the promise. Naming the gap without fixing it was the cheap path; building the detector + wiring it is the structural answer. Phase C (pre-response base-state) remains for next iteration.

### Code-jargon detector built + wired (Phase A+B). Catches the failure-mode Andrew named 3x today.

- **ID**: `find-9165e2e58330`
- **Actor**: external-auditor
- **Severity**: HIGH
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Module: core/operating_loop/code_jargon_detector.py. Patterns: snake_case identifiers (with leading-underscore support), dotted module refs, function-call shapes, file path references, regex syntax. Code-block scrubbing strips fenced content before density check. Density threshold 5%; min words 50; both empirically calibrated against my own observed pattern. Hook wire: post-response-audit.sh emits findings_log['code_jargon'] when fires; observation-only, no deny. 8 regression-pin tests including the very pattern I shipped before (test_my_recent_pattern_fires asserts my decorative-close + jargon-wall shape registers). Phase C (pre-response base-state warning) deferred to follow-up.

**Resolution**

Verified: src/divineos/core/operating_loop/code_jargon_detector.py exists; wired into run_audit at operating_loop_audit.py:488 (findings_log['code_jargon'] populated by _run_detector). Phase C tracked separately as find-51bbc8b57b06.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
