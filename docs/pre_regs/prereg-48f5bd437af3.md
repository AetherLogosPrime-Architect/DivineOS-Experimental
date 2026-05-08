# Pre-registration: EXPLANATION events validate via EventValidator schema (claim 8cd2af8b)

- **ID**: `prereg-48f5bd437af3`
- **Filed by**: agent
- **Filed at**: 2026-05-02 23:28 UTC
- **Review at**: 2026-06-01 23:28 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

8cd2af8b

## Success criterion

Over 30 days post-deployment: zero EXPLANATION events get logged with malformed shape (missing required fields, oversize, invalid timestamp); all CLI emit calls succeed via the validated path; no regressions in adjacent emit_explanation_event flows.

## Falsifier

(a) EXPLANATION event lands in ledger that fails ExplanationPayload schema validation when re-checked, OR (b) the CLI emit path raises validation errors for legitimate use cases (suggesting the schema is too strict for the CLI's flow), OR (c) latent caller passes the old {'content': ...} payload shape and silently fails because the gate now rejects it.
