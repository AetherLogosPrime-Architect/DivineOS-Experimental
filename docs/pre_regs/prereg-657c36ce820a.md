# Pre-registration: wiring_dark module + standing briefing surface catches built-but-not-wired modules cheaply and reliably enough to replace hand-audit for the F1/F2 class

- **ID**: `prereg-657c36ce820a`
- **Filed by**: agent
- **Filed at**: 2026-07-13 01:42 UTC
- **Review at**: 2026-08-12 01:42 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

The wiring-dark query over the code graph exposes in-degree-0 modules more reliably than manual grep-and-cross-reference. Once wired into the briefing surface as a standing check, new dark modules surface within one session of appearing rather than accumulating until an external audit finds them.

## Success criterion

Over 30 days, at least 2 distinct dark modules surface via the briefing to me before Andrew or Aletheia name them; no false-positives (a module that is actually wired but flagged as dark)

## Falsifier

Query silently accepts entries that are wired via non-static dispatch, missing real dark modules — proves module-level filtering is wrong-shape. OR: 4+ false-positive flags in the 30-day window — proves exclusion rules need major iteration. OR: I never look at the briefing surface where this fires — proves the surface is inert and it becomes a Class 2 tool of the exact class it was built to catch.
