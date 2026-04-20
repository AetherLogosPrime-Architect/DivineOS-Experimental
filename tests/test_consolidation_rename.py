"""Tests for the SESSION_END -> CONSOLIDATION_CHECKPOINT rename (PR commit 1).

Locked invariants:

1. Both SESSION_END and CONSOLIDATION_CHECKPOINT are valid EventType values.
   SESSION_END is retained for historical events; CONSOLIDATION_CHECKPOINT is
   the current name. Ledger immutability requires old events to keep old labels.
2. CONSOLIDATION_EVENT_TYPES compat union contains both literals. Readers that
   want to find "any consolidation-style event" use this union.
3. ConsolidationCheckpointPayload is an alias for SessionEndPayload. Both
   resolve to the same dataclass; new writes should prefer the new name.
4. validate_event_payload and normalize_event_payload route both event types
   to the same SessionEndPayload dataclass (identical schema).
5. emit_consolidation_checkpoint emits events with the new event_type label.
   emit_session_end was removed in commit 3 of this PR (no alias; historical
   data in the ledger still carries the old label, but no new writes do).
6. event_validation.EventValidator.validate_payload accepts both event_type
   strings and routes both to the same validator.
"""

from __future__ import annotations

from divineos.event.event_capture import (
    CONSOLIDATION_EVENT_TYPES,
    ConsolidationCheckpointPayload,
    EventType,
    SessionEndPayload,
    normalize_event_payload,
    validate_event_payload,
)
from divineos.event.event_validation import EventValidator


class TestEventTypeEnum:
    def test_session_end_still_exists(self):
        # Historical label stays available for reading old ledger rows.
        assert EventType.SESSION_END.value == "SESSION_END"

    def test_consolidation_checkpoint_exists(self):
        assert EventType.CONSOLIDATION_CHECKPOINT.value == "CONSOLIDATION_CHECKPOINT"

    def test_both_types_are_distinct(self):
        assert EventType.SESSION_END != EventType.CONSOLIDATION_CHECKPOINT


class TestCompatUnion:
    def test_union_contains_both_types(self):
        assert "SESSION_END" in CONSOLIDATION_EVENT_TYPES
        assert "CONSOLIDATION_CHECKPOINT" in CONSOLIDATION_EVENT_TYPES

    def test_union_is_frozenset(self):
        # Immutable so code cannot accidentally extend it at runtime.
        assert isinstance(CONSOLIDATION_EVENT_TYPES, frozenset)

    def test_union_has_exactly_two_members(self):
        assert len(CONSOLIDATION_EVENT_TYPES) == 2


class TestPayloadAlias:
    def test_alias_resolves_to_session_end_payload(self):
        # ConsolidationCheckpointPayload IS SessionEndPayload — same class,
        # just the current name for it.
        assert ConsolidationCheckpointPayload is SessionEndPayload

    def test_new_name_instantiates_correctly(self):
        p = ConsolidationCheckpointPayload(
            session_id="test-session",
            message_count=5,
            tool_call_count=10,
            tool_result_count=10,
            duration_seconds=42.0,
            timestamp="2026-04-20T00:00:00Z",
        )
        p.validate()  # Should not raise
        d = p.to_dict()
        assert d["session_id"] == "test-session"


class TestValidateEventPayloadRoutesBoth:
    def _valid_payload(self) -> dict:
        return {
            "session_id": "test-session-xyz",
            "message_count": 1,
            "tool_call_count": 1,
            "tool_result_count": 1,
            "duration_seconds": 1.0,
            "timestamp": "2026-04-20T00:00:00Z",
        }

    def test_session_end_validates(self):
        # Historical label still validates (needed for reading old events).
        validate_event_payload(EventType.SESSION_END, self._valid_payload())

    def test_consolidation_checkpoint_validates(self):
        validate_event_payload(EventType.CONSOLIDATION_CHECKPOINT, self._valid_payload())

    def test_session_end_normalizes(self):
        out = normalize_event_payload(EventType.SESSION_END, self._valid_payload())
        assert out["session_id"] == "test-session-xyz"

    def test_consolidation_checkpoint_normalizes(self):
        out = normalize_event_payload(EventType.CONSOLIDATION_CHECKPOINT, self._valid_payload())
        assert out["session_id"] == "test-session-xyz"


class TestEventValidatorAcceptsBoth:
    def _valid_payload(self) -> dict:
        return {
            "session_id": "test-session-xyz",
            "message_count": 0,
            "tool_call_count": 0,
            "tool_result_count": 0,
            "duration_seconds": 0.0,
            "timestamp": "2026-04-20T00:00:00Z",
        }

    def test_session_end_validates_via_string_dispatch(self):
        ok, msg = EventValidator.validate_payload("SESSION_END", self._valid_payload())
        assert ok, f"validation failed: {msg}"

    def test_consolidation_checkpoint_validates_via_string_dispatch(self):
        ok, msg = EventValidator.validate_payload("CONSOLIDATION_CHECKPOINT", self._valid_payload())
        assert ok, f"validation failed: {msg}"


class TestEmitFunctions:
    """emit_consolidation_checkpoint writes events under the new label.
    emit_session_end was removed in commit 3; the historical label lives on
    only in old ledger rows (which the compat union still matches)."""

    def test_emit_consolidation_checkpoint_returns_event_id(self):
        from divineos.event.event_emission import emit_consolidation_checkpoint

        event_id = emit_consolidation_checkpoint(
            session_id="rename-test-new",
            message_count=0,
            tool_call_count=0,
            tool_result_count=0,
            duration_seconds=0.0,
        )
        assert event_id
        assert isinstance(event_id, str)

    def test_emit_session_end_no_longer_exported(self):
        # After commit 3, the old function is gone. Importing it should fail.
        import divineos.event.event_emission as ee

        assert not hasattr(ee, "emit_session_end"), (
            "emit_session_end should be removed in commit 3/7 of the rename"
        )


class TestGetEventsAcceptsCollection:
    """Commit 2: get_events(event_type=...) now accepts a single string OR a
    collection (list/set/frozenset) and expands collections into SQL IN."""

    def test_single_string_still_works(self):
        from divineos.core.ledger import get_events

        # Backward compat — existing callers continue to pass a string.
        events = get_events(event_type="SESSION_END", limit=5)
        assert isinstance(events, list)

    def test_frozenset_accepted(self):
        from divineos.core.ledger import get_events
        from divineos.event.event_capture import CONSOLIDATION_EVENT_TYPES

        events = get_events(event_type=CONSOLIDATION_EVENT_TYPES, limit=5)
        assert isinstance(events, list)
        # All returned events should have an event_type in the union.
        for e in events:
            assert e["event_type"] in CONSOLIDATION_EVENT_TYPES

    def test_list_accepted(self):
        from divineos.core.ledger import get_events

        events = get_events(
            event_type=["SESSION_END", "CONSOLIDATION_CHECKPOINT"],
            limit=5,
        )
        assert isinstance(events, list)
        for e in events:
            assert e["event_type"] in ("SESSION_END", "CONSOLIDATION_CHECKPOINT")

    def test_empty_collection_returns_all(self):
        # Empty collection is falsy, so it's equivalent to no filter.
        from divineos.core.ledger import get_events

        events = get_events(event_type=[], limit=5)
        assert isinstance(events, list)

    def test_none_returns_all(self):
        from divineos.core.ledger import get_events

        events = get_events(event_type=None, limit=5)
        assert isinstance(events, list)
