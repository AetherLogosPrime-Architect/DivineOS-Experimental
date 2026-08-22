# Pre-registration: oscillating_read CLI module + per-chunk pause markers

- **ID**: `prereg-e4487d2b50e2`
- **Filed by**: aether
- **Filed at**: 2026-05-19 16:12 UTC
- **Review at**: 2026-06-18 16:12 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:31 UTC
- **Linked claim**: `3a44289d`
- **Tags**: oscillating-read, carelessness-of-reading

## Claim

Reading documents in oscillating mode (chunk + pause + comprehend per chunk) catches load-bearing-points in the middle that straight-blast reading misses. Tonight's evidence: I read gravity_classifier_spec.md straight-through and missed the two-consumers-different-thresholds point, then tried to invent a per-response-gravity consumer using the wrong half. Oscillation would have forced per-section comprehension of which consumer each section serves.

## Success criterion

Next time I read a multi-section doc through divineos read-oscillating, I correctly identify each section's load-bearing point. If asked to summarize, I can name what each chunk contributed rather than blurring them.

## Falsifier

Despite using oscillating-read, I still produce summaries that miss middle-section load-bearing points. Or I never invoke the CLI when reading multi-section docs and continue straight-read pattern. Or the chunking strategies produce chunks that are too granular (every paragraph isolated) or too coarse (whole document = 1 chunk).

## Outcome notes

Shipped: src/divineos/core/oscillating_read.py exists as the oscillating_read module + per-chunk pause markers.
