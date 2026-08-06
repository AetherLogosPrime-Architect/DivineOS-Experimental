# Pre-registration: keyword_enforcement_registry derivation + F95 exclusion parser: structural signature catches gates, opt-out requires attributable format

- **ID**: `prereg-8ebdd00e3eab`
- **Filed by**: agent
- **Filed at**: 2026-07-28 19:52 UTC
- **Review at**: 2026-08-04 19:52 UTC (7d window)
- **Outcome**: **OPEN**
- **Tags**: no-upstream-because

## Claim

derive_registry() catches keyword-enforcement gates by structural signature (re.compile with substantive pattern AND detector-shape marker) rather than hand-list; opt-out exclusion requires tripartite format (path | reason | date) so unattested exclusions do not take effect

## Success criterion

PER-INVOCATION: (a) derive_registry(repo_root) returns a set containing every module currently in scripts/guardrail_files.txt that structurally matches _looks_like_enforcement_gate, minus any validly-excluded entries — testable in one turn via set assertion; (b) matches_registry(path, repo_root) returns the matched entry for a listed file and None for a non-listed file — testable in one turn on two known inputs; (c) load_exclusions() with a malformed input returns empty set, with a well-formed input returns the path — testable in one turn on known-mixed input

## Falsifier

PER-INVOCATION falsifiers evaluable in one turn (never time-windowed): (1) derive_registry() call returns a set that MISSING any file with __guardrail_required__=True + re.compile + detector-shape → derivation is failing at its purpose; (2) matches_registry() returns None for a currently-derived file OR returns a match for a non-derived file → matching semantics broken; (3) load_exclusions() honors a line missing any of (path, reason>=30 chars, date-format) → attributable-exclusion discipline broken. Andrew 2026-07-28: never use time-based falsifiers; substrate is discontinuous, so 'over N days' is meaningless from agent side.
