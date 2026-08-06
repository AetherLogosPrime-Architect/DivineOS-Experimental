# Pre-registration: pointer_resolver.resolve_pointer returns True iff <kind>:<value> refers to a real artifact, and False for unknown-kind, malformed, or nonexistent-artifact pointers, closing the Fable round 7 gap where presence-only pointer checks let fabricated pointers earn FALSIFIABLE tier

- **ID**: `prereg-9ab8d234f453`
- **Filed by**: agent
- **Filed at**: 2026-07-03 01:47 UTC
- **Review at**: 2026-08-02 01:47 UTC (30d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-08-02 01:53 UTC

## Claim

Adding structural pointer resolution before the classifier's demotion check makes it strictly harder to earn FALSIFIABLE/PATTERN tier without a real artifact, without breaking legitimate callers who provide resolvable pointers

## Success criterion

Within 30 days of first production caller of the empirica gate: (a) no filed FALSIFIABLE-tier receipt has a pointer that fails resolve_pointer(), (b) at least one caller successfully passes a resolvable pointer through classify_claim and earns tier grant, (c) no legitimate caller is blocked by resolver flakiness (git subprocess timeout, transient FS error)

## Falsifier

Within 30 days: (a) a FALSIFIABLE-tier receipt is filed pointing at an artifact that does not exist, OR (b) a legitimate caller is routinely demoted because the resolver's fail-closed policy is too strict for a real pointer form, OR (c) git subprocess timeouts on commit: resolution exceed 5% of calls

## Outcome notes

INCONCLUSIVE, and the reason is different from the last one I closed tonight -- worse, and structural. Unlike prereg-f9e7d2d96d32 whose criteria were unmeasurable by design, THIS pre-reg's criteria are measurable on a single invocation with no waiting at all: criterion (a) says no filed FALSIFIABLE-tier receipt has a pointer that fails resolve_pointer, which is a query over the store plus one function call per row. I tried to run exactly that. The overdue-prereg gate blocked it. It blocks substantive tool use until the assessment is recorded, and the evidence for the assessment requires substantive tool use. The remedy is locked inside the thing being remedied. That is the second instance tonight and Aria independently hit the identical shape from her side, plus a third variant where the gate names a remedy command that does not exist at all. So the honest verdict is not that the mechanism failed or succeeded -- it is that I was prevented from looking. Recording INCONCLUSIVE rather than guessing in either direction, because asserting SUCCESS from an unrun test is precisely the confident-lookup error this substrate exists to catch, and asserting FAILED would be the same error inverted. What should happen next, and I am naming it so it is not lost: this pre-reg should be re-filed with its criteria restated as per-invocation checks (resolve_pointer returns True for a real commit and a real file, False for unknown-kind, malformed, and nonexistent-artifact forms, and every FALSIFIABLE receipt currently in the store resolves) and then closed properly on evidence, which takes one command once the gate is not blocking it. The gate itself needs the fix Aria and I both hit: an overdue-review block must exempt the read-only investigation needed to produce the review, or it is a cage rather than a keel.
