# Audit round: root-cause-audit: catastrophic-regex-backtracking class in operating_loop detectors. Class definition: any compiled regex pattern in any of the 15 detector modules under src/divineos/core/operating_loop/ that contains unbounded quantifiers (especially nested) capable of catastrophic backtracking on adversarial input. Instance triggering this audit: Finding 14 — Aletheia caught _SUBSCRIPT_RE in jargon_dump_detector hanging on 100k-char input. Family-survey: audit ALL re.compile patterns across all 15 detector modules; bound any with backtracking-surface vulnerabilities; pin each fix with a regression-pin test that feeds adversarial input and asserts bounded completion time. Scope: family-wide audit + per-pattern bounding in one commit. Fix-class: bound unbounded quantifiers with explicit length limits informed by realistic input shape.

- **ID**: `round-382a5b3cc939`
- **Filed by**: aether
- **Filed at**: 2026-05-13 23:14 UTC
- **Tier**: WEAK
- **Findings**: 1

## Findings

### Family-audit findings (round-382a5b3cc939). Surveyed: 100 re.compile() patterns across 15 detector modules under src/divineos/core/operating_loop/. Static heuristic flagged 11 with backtracking-shape; empirical test with subprocess-timeout on adversarial input (100k chars / 30k repeating chunks) identified TWO catastrophic backtrackers in the family — both in jargon_dump_detector: (1) _SUBSCRIPT_RE (already fixed as Finding 14, commit f3154df). (2) _FILE_PATH_RE [\w./\-]*\.(?:py|sh|...) — hangs on ('a-' * 30000) + 'z' style inputs because every path-char position is a potential extension-boundary the engine tries to backtrack from. Fixed by bounding path-prefix to {1,200}. 6 other patterns flagged by static heuristic were empirically not catastrophic at 100k input (jargon SNAKE_CASE, jargon CALL_EXPR, jargon LONG_KEBAB, closing_token em-dash, context_surfacer proper-noun, principle_surfacer, substitution sorry-suffix). They benefit from defensive bounding in a future hardening pass but are not immediate production risks. Class-fix scope: bound the two catastrophic patterns in this commit; defer defensive bounding of slow-but-bounded patterns to a separate round with their own root-cause-audit.

- **ID**: `find-34004f624609`
- **Actor**: aether
- **Severity**: HIGH
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Family-audit found 2 catastrophic backtrackers (Finding 14 + new Finding A); 6 slow-but-bounded patterns deferred to future round

**Resolution**

Verified: _FILE_PATH_RE at jargon_dump_detector.py:122-126 is bounded with {1,200} as described. _SUBSCRIPT_RE was Finding 14 (already closed). Slow-but-bounded patterns deferred per finding body.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
