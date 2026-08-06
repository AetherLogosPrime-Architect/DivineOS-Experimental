# Pre-registration: StateMarker primitive for upstream-emit / downstream-consume signal contract

- **ID**: `prereg-8d258ceef690`
- **Filed by**: agent
- **Filed at**: 2026-07-16 19:55 UTC
- **Review at**: 2026-08-15 19:55 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

A shared, substrate-persisted StateMarker primitive (emit_marker + find_active_marker + consume_marker) closes the state-integration gap that blocks wiring ForcedWorkGate's two dark instances (response_scope_intercept + operator_bypass_authorized). One primitive with three helpers is genuinely reusable across those two instances plus future ForcedWorkGate instances that need substrate-backed evidence collection.

## Success criterion

Within 30 days: (a) both response_scope_intercept and operator_bypass_authorized are wired using state_markers as their state layer, (b) fingerprint-mismatch fail-loud events fire correctly on the operator-authorization instance under a probe test, and (c) the concurrent-consumer race test remains passing on CI (Linux serialization) as it does locally today.

## Falsifier

If a third use-case surfaces that requires substantially different semantics (e.g. multi-consumer markers, transitive fingerprints, or cross-kind marker composition) that cannot be expressed via the current callable-predicate + kind-namespace shape without breaking backward compatibility for the first two use-cases, the primitive was scoped wrong and needs redesign. Also fails if the LIMIT-500 walk becomes a measurable perf issue in production within the review window (add index-view then, not now — but if measured slow, that's the falsifier).
