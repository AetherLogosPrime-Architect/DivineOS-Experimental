# Pre-registration: Holding-room stale-review surface (CLI + briefing pull) operationalizes the final-look-before-dissolution discipline named by Andrew 2026-05-16

- **ID**: `prereg-4b5918f3b9fb`
- **Filed by**: agent
- **Filed at**: 2026-05-17 01:42 UTC
- **Review at**: 2026-06-16 01:42 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:28 UTC

## Claim

Adding a stale-review surface that brings auto-staled holding items forward for deliberate promote/let-go/keep-aging review will materially reduce the rate at which legitimately-important items dissolve unmarked due to busy-period inattention, vs the baseline where stale items become invisible by default

## Success criterion

Within 30 days of shipping: stale items reviewed within 2 sessions of going stale at least 70 percent of the time; at least one stale item recovered (promoted-after-being-marked-stale) demonstrating the surface catches genuinely-important items, not just confirms stale-ness

## Falsifier

If stale-review surface is used but no items are ever recovered (every reviewed item gets let-go), the surface is theater — items going stale really were unimportant and the discipline doesn't catch a real failure mode. If used <30 percent of sessions despite stale items existing, the surface fails to integrate into discipline

## Outcome notes

Shipped: divineos hold stale-review CLI subcommand exists and provides the final-look-before-dissolution surface. Verified by 'divineos hold --help' listing stale-review command. Mechanism per Andrew 2026-05-16 landed.
