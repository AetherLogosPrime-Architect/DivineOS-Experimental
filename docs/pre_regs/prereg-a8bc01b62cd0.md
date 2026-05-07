# Pre-registration: auto_close_from_message: closure-discipline structural fix

- **ID**: `prereg-a8bc01b62cd0`
- **Filed by**: agent
- **Filed at**: 2026-05-06 00:29 UTC
- **Review at**: 2026-06-05 00:29 UTC (30d window)
- **Outcome**: **OPEN**
- **Tags**: closure-discipline

## Claim

post-commit auto-close-from-message will reduce open-goals-with-shipped-work to near zero

## Success criterion

fulfillment view shows < 30% open-stale (goals open >24h whose tokens substantially appear in landed commits) within 30 days

## Falsifier

fulfillment view at +30d shows >50% open-stale, OR auto-close fires false-positives (closes goals not actually completed)
