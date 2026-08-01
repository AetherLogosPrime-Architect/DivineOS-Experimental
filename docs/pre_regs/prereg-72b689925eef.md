# Pre-registration: correction_shape three-feature semantic detector replaces keyword-band-aid classify_correction in correction_marker.py; fires iff addressee=me AND stance=evaluative-negative AND subject=my-action all co-occur (binary, no middle tier)

- **ID**: `prereg-72b689925eef`
- **Filed by**: agent
- **Filed at**: 2026-07-22 22:05 UTC
- **Review at**: 2026-08-05 22:05 UTC (14d window)
- **Outcome**: **OPEN**

## Claim

The three-feature discriminator eliminates the WEAK-keyword-partial-match false-fire class the prior implementation accumulated 807 lines of patches for. First live-fire class (even-if hypothetical) already caught and refined mid-session as validation.

## Success criterion

After 14 days of production use: (a) no more than 2 andrew-correction filings per week from false-positive gate fires (baseline 2026-07-22 session: 6 false-fires in one session), (b) DOGFOOD test suite remains 100% passing, (c) at least one true-positive fire caught a real correction that the prior keyword detector would have missed OR the marker-file protocol contract remained stable per test_correction_marker.py's 35 preserved tests.

## Falsifier

If any of: (a) false-fire rate exceeds 3+ per week for 2 consecutive weeks, or (b) DOGFOOD tests need to be relaxed to accommodate a real correction the detector missed, or (c) a class of correction Aria + I did not anticipate fires 3+ times without our design catching it. Then the semantic layer is under-specified and needs a stricter feature-3 subject-check (likely NLI-classifier or explicit prior-turn parse rather than keyword completion-claim heuristic).
