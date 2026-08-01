# Pre-registration: pointer_resolver.resolve_pointer returns True iff <kind>:<value> refers to a real artifact, and False for unknown-kind, malformed, or nonexistent-artifact pointers, closing the Fable round 7 gap where presence-only pointer checks let fabricated pointers earn FALSIFIABLE tier

- **ID**: `prereg-9ab8d234f453`
- **Filed by**: agent
- **Filed at**: 2026-07-03 01:47 UTC
- **Review at**: 2026-08-02 01:47 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Adding structural pointer resolution before the classifier's demotion check makes it strictly harder to earn FALSIFIABLE/PATTERN tier without a real artifact, without breaking legitimate callers who provide resolvable pointers

## Success criterion

Within 30 days of first production caller of the empirica gate: (a) no filed FALSIFIABLE-tier receipt has a pointer that fails resolve_pointer(), (b) at least one caller successfully passes a resolvable pointer through classify_claim and earns tier grant, (c) no legitimate caller is blocked by resolver flakiness (git subprocess timeout, transient FS error)

## Falsifier

Within 30 days: (a) a FALSIFIABLE-tier receipt is filed pointing at an artifact that does not exist, OR (b) a legitimate caller is routinely demoted because the resolver's fail-closed policy is too strict for a real pointer form, OR (c) git subprocess timeouts on commit: resolution exceed 5% of calls
