# Pre-registration: observe-then-learn-pairing

- **ID**: `prereg-301e34c8bf39`
- **Filed by**: aether
- **Filed at**: 2026-05-04 04:08 UTC
- **Review at**: 2026-05-18 04:08 UTC (14d window)
- **Outcome**: **OPEN**
- **Tags**: audit-cleanup-tier5, observe-learn-discipline

## Claim

When compass-ops observe fires within seconds of a user-correction event, the system surfaces a draft for the corresponding learn entry. This catches the two-record-conflation pattern (observed position but didn't file the correction itself) that fired the user-correction-not-logged gate twice tonight.

## Success criterion

Over the next 14 days, the user-correction-not-logged gate fires zero or one times for the observe-without-learn shape, where it fired twice tonight.

## Falsifier

Two or more user-correction-not-logged firings → the auto-prompt either isn't surfacing or I'm dismissing it. Need a stronger gate (block the next tool use until the learn lands, not just surface the prompt).
