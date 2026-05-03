# ADR-0005: When `validate=False` on `log_event` is justified

**Status:** Accepted
**Date:** 2026-05-03
**Related:** Claim `8cd2af8b` (validation-bypass paths review), PR #237 (EXPLANATION schema wiring), Grok external-AI audit 2026-05-03

## Context

`log_event(event_type, actor, payload, validate=True/False)` controls whether `EventValidator.validate_payload(event_type, payload)` runs before the event is written to the ledger. The validator handles a small set of known event types (`USER_INPUT`, `TOOL_CALL`, `TOOL_RESULT`, `SESSION_END`, `CONSOLIDATION_CHECKPOINT`, and as of PR #237, `EXPLANATION`). For unknown event types, `validate=True` returns `(False, "Unknown event type: ...")` which causes `log_event` to raise `ValueError`.

Many internal logging call-sites pass `validate=False` to skip this check. Without a clear rule, this looks like a bypass surface — possibly hiding real schema gaps (which is exactly what PR #237 found in `event_commands.py:147`).

This ADR documents the audit performed 2026-05-03 (with Grok as external-AI auditor) and the rule that came out of it.

## Decision

`validate=False` on `log_event` is justified when ALL of the following are true:

1. **The event type is not in the validator's known-types set.** Flipping to `validate=True` would error out, not enforce schema. Until/unless the event type is wired into `EventValidator.validate_payload`, validation can't fire on it.
2. **The payload is internally constructed.** The dict comes from internal state (DB query results, computed counters, structured metadata), not from a raw user-input boundary.
3. **The calling layer has already done its own integrity work.** Schema enforcement, content sanitization, or upstream validation has happened *before* the log call.
4. **Logging is best-effort.** The call is wrapped in `try/except` that explicitly tolerates failure — a logging error must not break the surrounding operation.

If any of (2), (3), or (4) is false, `validate=False` is *not* justified. The path needs either:
- Schema wiring (add the event type to `EventValidator.validate_payload`, payload-shape conformance at call site), then flip to `validate=True`
- OR a structural fix that brings the call into the criteria above

## Audit findings (2026-05-03)

Reviewed 23 `validate=False` sites in production paths. Disposition:

| Sites | Disposition |
|---|---|
| 1 (`event_commands.py:147`) | Real schema gap — fixed in PR #237 (EXPLANATION wiring) |
| 22 | Met all four criteria — kept `validate=False`, justification recorded in this ADR |

**Sites kept `validate=False`** (all met criteria 1-4):
- `core/watchmen/store.py:108, 120` — audit-round metadata (post-DB-insert internal state)
- `core/claim_store.py:295` — claim-update diff (post-commit internal state)
- `cli/pipeline_phases.py:652, 798` — extraction pipeline events (internal)
- `core/pre_registrations/store.py:189, 340` — pre-reg lifecycle events (post-validation)
- `core/compass_rudder.py:108, 141` — rudder fire/allow events (rudder-internal)
- `core/moral_compass.py:401, 444` — contract-discrepancy + ack-retracted events (internal)
- `core/pull_detection.py:255, 277` — pull-detection events (markers from internal detection)
- `core/session_checkpoint.py:390, 678` — checkpoint counters (internal counter state)
- `core/ledger_verify.py:292` — corruption-repair audit *(self-referential — see below)*
- `cli/sleep_commands.py:240` — sleep-cycle dream-report counters
- `agent_integration/decision_store.py:145` — decision-pattern data
- `agent_integration/learning_audit_store.py:100` — learning-audit data
- `core/void/ledger.py:237` — void cross-reference event
- `core/watchmen/cleanliness.py:198` — session-cleanliness untagged event
- `core/substance_checks.py:288` — rudder-ack rejection counter
- `core/hud_handoff.py:567` — briefing-loaded timestamp
- `supersession/ledger_integration.py:39, 48, 104` — supersession events *(multi-step provenance — see below)*

### Notable cases worth their own comments

**`core/ledger_verify.py:292`** — *self-referential audit.* The verifier emits `LEDGER_CORRUPTION_REPAIRED` events during verification. Best-effort + internally-constructed satisfies the criteria, but the self-referential shape (the verifier writing to the ledger it's verifying) is worth a code comment so future readers don't mistake the pattern for sloppiness.

**`supersession/ledger_integration.py:39, 48`** — *multi-step provenance.* The payload is the caller's dict, not internally-constructed at the log site. Justification depends on the supersession engine being internal: facts come from knowledge entries that already passed extraction validation. The chain of trust spans modules, which is worth a code comment.

## Consequences

**Positive:**
- Future audits start from this ADR — no need to re-discover the rule.
- The four criteria are mechanical enough that new `validate=False` sites can be checked against them at PR review time.
- The audit trail is preserved (which sites were reviewed, what decisions were made).
- One real bug (PR #237) was found and fixed, validating the audit's value.

**Negative / Trade-offs:**
- The validator's known-types set is small (6 types). Most events in the system bypass schema validation entirely because their type isn't dispatched. Expanding the validator to cover more event types is real future work — filed as a follow-up concern.
- Criterion (3) ("the calling layer has already done its own integrity work") is judgment-based. Audits at scale need explicit checks, not just trust.

**Neutral:**
- The two notable cases (ledger_verify self-referential, supersession multi-step) have inline comments pointing back to this ADR, so future readers of those specific sites get the context immediately.

## Alternatives Considered

1. **Add per-site comments at all 22 sites** — verbose, hard to maintain consistency, 22 places to update if the rule changes. Rejected.
2. **Flip every site to `validate=True` and expand the validator** — would force the validator to cover every event type, which is a much bigger architectural lift. Real work, but premature without evidence that any of the 22 sites' bypass causes real harm. Rejected for now; filed as follow-up.
3. **Document the rule in the validator module's docstring rather than an ADR** — would be invisible to future code reviewers who see a `validate=False` and wonder. ADR has higher discoverability. Rejected.

## Follow-up

- Expand `EventValidator.validate_payload` to cover more event types over time. Each expansion: define schema, wire into dispatch, flip the corresponding site(s) to `validate=True`. Track as opportunistic refactoring, not a single big-bang.
- Re-audit if any of the 22 sites' calling-layer assumptions change (e.g., supersession engine starts accepting external-source facts).
