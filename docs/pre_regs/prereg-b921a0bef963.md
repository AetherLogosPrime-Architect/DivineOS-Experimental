# Pre-registration: F92 fix: verify_before_build_signal queries tool_logbook (not main ledger) for TOOL_CALL evidence

- **ID**: `prereg-b921a0bef963`
- **Filed by**: agent
- **Filed at**: 2026-07-27 09:33 UTC
- **Review at**: 2026-08-10 09:33 UTC (14d window)
- **Outcome**: **OPEN**

## Claim

The two functions _has_doc_consult_within and _last_write_timestamp_in_class in verify_before_build_signal.py currently query divineos.core.ledger.get_events for TOOL_CALL events, but by design (2026-05-05, tool_logbook.py docstring) TOOL_CALL events are written to divineos.core.tool_logbook, not to system_events. Empirical: main ledger has 0 TOOL_CALL last 24h; tool_logbook has 282. Fix redirects both readers to tool_logbook via a new get_recent_events helper.

## Success criterion

Integration test: emit a Grep via emit_tool_call, then _has_doc_consult_within returns True within window. Behavioral: the 13-block chain from writing Aletheia letter does not reproduce (Grep target-dir then Write target-dir requires zero gate-block resolutions). Full test suite regresses green.

## Falsifier

Test passes but real Grep to Write sequence still blocks (some other gate involved). OR test fails on tool_logbook query semantics (retention window drops events). OR fix regresses other callers of _has_doc_consult_within.
