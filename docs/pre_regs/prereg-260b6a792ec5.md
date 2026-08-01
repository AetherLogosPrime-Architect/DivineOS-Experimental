# Pre-registration: Adopt the flagship's disclose-then-escalate compass-gate redesign into Experimental (marker + gate 1.47 + dismissal surface + dismiss CLI)

- **ID**: `prereg-260b6a792ec5`
- **Filed by**: agent
- **Filed at**: 2026-05-27 23:55 UTC
- **Review at**: 2026-06-17 23:55 UTC (21d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:32 UTC

## Claim

Disclose-then-escalate (advisory below ESCALATION_THRESHOLD=2, hard-block at/above, per-turn dedup) is better than the current hard-block-every-tool-call because it removes within-turn wallpaper noise (precision-increase) while preserving enforcement (still blocks after 2 ignored advisories)

## Success criterion

Aletheia verifies escalation reliably fires (test_block_at_threshold green), no within-turn re-fire spam in practice, dismissal-rate surfacing works; net fewer gate-gaming incidents

## Falsifier

Escalation does NOT reliably fire — dedup + 2-advisory grace combine so advised_count rarely reaches threshold, degrading the gate to a de-facto ignorable advisory (the demote-to-warning failure Aletheia rejected); OR dismissal becomes a routine bypass rather than rare exception

## Outcome notes

Shipped: src/divineos/core/compass_dismissal_briefing_surface.py exists as part of the disclose-then-escalate compass-gate mechanism. The dismissal surface + gate 1.47 landed.
