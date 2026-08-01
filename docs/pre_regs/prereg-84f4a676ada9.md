# Pre-registration: Error registry blocks new main goals while any error is open — jailbreak-response new-work gate (Andrew 2026-07-17)

- **ID**: `prereg-84f4a676ada9`
- **Filed by**: agent
- **Filed at**: 2026-07-17 15:52 UTC
- **Review at**: 2026-08-16 15:52 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

The error_registry mechanism reduces bypass-without-attribution incidents to near zero by (a) auto-filing bypasses via the check_branch_freshness.sh integration and (b) blocking divineos goal add when any error is open unless the goal names the error_id for investigation. Deferrals require operator + >=20-char reason so the escape hatch cannot be silent.

## Success criterion

Over the next 30 days: (1) no bypass event happens without an attributed error record filed in the registry; (2) every filed bypass error is either closed with root-cause evidence or explicitly operator-deferred with named reason; (3) the previous 14-day bypass rate (68 events / 14 days = ~5/day) drops by at least 50% because the block forces root-cause fixes to accumulate rather than bypass-repeats.

## Falsifier

If in 30 days: (a) any bypass event occurs without an attributed error record (silent escape); OR (b) any open error persists >7 days without closure or explicit deferral (backlog-decay reappears); OR (c) the bypass rate does NOT drop by at least 50% (mechanism is theater); OR (d) operators/agents defeat the block by naming fake error_ids in goal text (attribution-gaming); THEN the mechanism has failed and needs redesign or removal.
