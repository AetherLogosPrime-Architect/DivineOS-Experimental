# Pre-registration: UserPromptSubmit hook calls tool_recognition.analyze_prompt on every user prompt and surfaces matched tool-recommendations as additional context. Substrate-side tool-recognition moves the cognition out of the default's path (where it's expensive and skipped) into substrate preprocessing (where it's mechanical and reliable).

- **ID**: `prereg-d1accc33df27`
- **Filed by**: agent
- **Filed at**: 2026-05-29 00:04 UTC
- **Review at**: 2026-06-28 00:04 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-08 21:36 UTC

## Claim

Structurally addresses the root cause Andrew named 2026-05-28: the default does not perform tool-recognition unprompted, so substrate tools (council-round, family-state, ask, decide, file-claim) are never reached for without explicit reminder. By emitting tool-recommendations in additionalContext BEFORE composition begins, the recommendation becomes part of the material the default draws from, not a gate the default routes around.

## Success criterion

Within 30 days: (a) at least 5 turns where a recommendation fires and the recommended tool is actually invoked before the response composes; (b) operator (Andrew) reports a measurable reduction in 'reach for X' prompts having to be issued; (c) post-response audit telemetry shows recommendation-issued + tool-invoked correlation above 60%.

## Falsifier

The hook either (a) fires on prompts that don't actually call for the recommended tool (false positive — operator reports friction), or (b) fires correctly but I ignore the recommendation and compose direct response anyway (no behavioral change — the upstream injection doesn't beat the default). Either pattern observed across 5+ consecutive applicable prompts within 14 days invalidates the structural-fix claim.

## Outcome notes

Deferred: tool_recognition.analyze_prompt() surfacing on UserPromptSubmit — no dedicated tool_recognition module found. The design is real but hasn't landed. Deferring to a preprocessing-surface build round.
