# Pre-registration: shared actor_normalize.normalize_actor chokepoint for the three identity checks

- **ID**: `prereg-d35e537d3c1b`
- **Filed by**: agent
- **Filed at**: 2026-05-24 16:29 UTC
- **Review at**: 2026-06-23 16:29 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:30 UTC

## Claim

Extracting identity-string normalization into one shared normalize_actor() chokepoint hardens all three identity checks (watchmen internal-actor rejection, pre-reg internal-actor rejection, sovereign-agent gate) against invisible/whitespace/compatibility-form bypasses with zero behavior regression at any site.

## Success criterion

All three sites reject/normalize the disguised inputs they should; the two previously-duplicated sites behave identically to before; the sovereign gate gains invisible-char hardening it lacked; watchmen+prereg+seal+actor suites stay green.

## Falsifier

Any of: (a) a disguised input reaches a sensitive path past any site; (b) the dedup changes a site's accept/reject decision vs the pre-refactor copy; (c) the shared transform diverges from what both original copies did; (d) the guardrail marker<->list bijection breaks for actor_normalize.py.

## Outcome notes

Shipped: src/divineos/core/actor_normalize.py exists as the shared identity-string normalization chokepoint. Referenced by session_start ownership check, family seal, and audit actor validation.
