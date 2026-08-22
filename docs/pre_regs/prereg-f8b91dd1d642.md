# Pre-registration: Context-aware tiered correction-detection: STRONG patterns block; WEAK patterns ('that doesnt','you only') block only if the prior turn was correctable (completion-claim or substantive edit), else advise (non-blocking surface)

- **ID**: `prereg-f8b91dd1d642`
- **Filed by**: agent
- **Filed at**: 2026-06-04 16:15 UTC
- **Review at**: 2026-07-04 16:15 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-11 01:54 UTC

## Claim

Eliminates weak-pattern false-fires (blocked edits + compass-cascades) without losing recall on real corrections

## Success criterion

Known false-fires ('that doesnt mean were done', 'you only need to relax') no longer BLOCK; real corrections (strong, or weak-after-claim/action) still caught

## Falsifier

A real correction gets MISSED — advised-not-blocked when it was genuinely corrective (e.g. a weak-pattern correction after a non-substantive turn), OR a known false-fire still blocks

## Outcome notes

Context-aware tiered correction-detection lives in src/divineos/core/correction_marker.py: STRONG vs WEAK pattern split, _has_corrective_context disambiguator with prior-turn signal (completion-claim or substantive-tool), epistemic-complement guard for that-doesnt patterns (Aletheia HOLD #85). Verified via grep of STRONG_CORRECTION / WEAK_CORRECTION / _has_corrective_context in correction_marker.py and analysis/session_analyzer.py.
