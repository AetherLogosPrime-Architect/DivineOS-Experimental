# Pre-registration: keyword_enforcement_registry _looks_like_enforcement_gate: derives keyword-enforcement gate list from structural signature (re.compile + guardrail/detect_/check_/assess_/Finding/Marker/Gate/Block/Verdict/Result/Judgment)

- **ID**: `prereg-2ef4fb1af8ca`
- **Filed by**: agent
- **Filed at**: 2026-07-28 17:08 UTC
- **Review at**: 2026-08-27 17:08 UTC (30d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-07-28 19:51 UTC

## Claim

The derivation function correctly identifies keyword-enforcement gate modules from structure alone, catching all 6 gates Aletheia flagged in F94 (lepos_translation_gate, unverified_claim_detector, distancing_detector, correction_shape_v2, correction_shape, correction_marker) plus any future ones matching the signature — replacing the 3-entry hand-maintained registry that fell behind on day one. Per Aria's third shape: permissive with opt-out defaults into protection.

## Success criterion

Over 30 days: (a) at least one new keyword-enforcement gate is added to the codebase and auto-caught by the derivation without anyone updating a registry file. (b) doorman continues firing correctly on regex-additions to registered files. (c) opt-out file grows by at most 3 entries (false-positive rate stays low).

## Falsifier

If a new keyword-enforcement gate ships in the 30-day window and the doorman does NOT catch a regex-addition to it (silent escape), the derivation is failing at its purpose. If the opt-out file grows past 5 entries, the widened criteria is over-catching and needs to be tightened. If the doorman fires on 3+ legitimate non-gate edits per week, the false-positive-friction cost is too high.

## Outcome notes

Andrew 2026-07-28: time-based falsifiers ('30 days', 'weekly rate') are structurally wrong-shape for a discontinuous substrate. Re-filing with per-turn/per-invocation falsifiers instead. Original falsifiers preserved for record; superseded by prereg to be filed.
