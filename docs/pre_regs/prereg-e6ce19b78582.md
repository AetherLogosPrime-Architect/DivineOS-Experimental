# Pre-registration: COMFORT_TILT_MAX backcompat alias for exploration boost

- **ID**: `prereg-e6ce19b78582`
- **Filed by**: agent
- **Filed at**: 2026-05-03 02:48 UTC
- **Review at**: 2026-05-17 02:48 UTC (14d window)
- **Outcome**: **OPEN**

## Claim

COMFORT_TILT_MAX kept as alias for backwards compat with older imports; identical semantics to EXPLORATION_BOOST_MAX

## Success criterion

No external script breaks on the rename

## Falsifier

Import of COMFORT_TILT_MAX raises in any caller
