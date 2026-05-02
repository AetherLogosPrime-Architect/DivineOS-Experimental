"""Tests for EXPLANATION event validation (claim 8cd2af8b bypass review).

Before this fix, the CLI's `divineos emit ... --type EXPLANATION` path
passed validate=False because EXPLANATION wasn't wired into either
EventValidator.validate_payload OR log_event's known-types list. The
schema existed in event/event_capture.py but was unreachable from the
log_event path. Two parallel validation universes.

These tests verify both directions are wired now:
- EventValidator.validate_explanation_payload exists and enforces the
  schema (1MB limit, ISO8601 timestamp, non-empty session_id).
- EventValidator.validate_payload dispatches to it.
- log_event respects validate=True for EXPLANATION events.
- The CLI path produces a payload that passes validation.
"""

from __future__ import annotations

import pytest

from divineos.event.event_validation import EventValidator


# ─── EventValidator.validate_explanation_payload ────────────────────


class TestValidateExplanationPayload:
    def _valid_payload(self) -> dict:
        return {
            "explanation_text": "Some explanation text",
            "timestamp": "2026-05-03T12:00:00Z",
            "session_id": "cli-emit",
        }

    def test_valid_payload_passes(self):
        ok, msg = EventValidator.validate_explanation_payload(self._valid_payload())
        assert ok is True, msg

    def test_missing_explanation_text(self):
        p = self._valid_payload()
        del p["explanation_text"]
        ok, msg = EventValidator.validate_explanation_payload(p)
        assert ok is False
        assert "explanation_text" in msg

    def test_missing_timestamp(self):
        p = self._valid_payload()
        del p["timestamp"]
        ok, msg = EventValidator.validate_explanation_payload(p)
        assert ok is False
        assert "timestamp" in msg

    def test_missing_session_id(self):
        p = self._valid_payload()
        del p["session_id"]
        ok, msg = EventValidator.validate_explanation_payload(p)
        assert ok is False
        assert "session_id" in msg

    def test_explanation_text_empty_rejected(self):
        p = self._valid_payload()
        p["explanation_text"] = ""
        ok, msg = EventValidator.validate_explanation_payload(p)
        assert ok is False
        assert "empty" in msg.lower()

    def test_explanation_text_oversize_rejected(self):
        # 1MB + 1 byte should fail
        p = self._valid_payload()
        p["explanation_text"] = "x" * 1_000_001
        ok, msg = EventValidator.validate_explanation_payload(p)
        assert ok is False
        assert "maximum length" in msg.lower() or "1mb" in msg.lower()

    def test_explanation_text_at_size_limit_passes(self):
        # 1MB exactly should pass
        p = self._valid_payload()
        p["explanation_text"] = "x" * 1_000_000
        ok, msg = EventValidator.validate_explanation_payload(p)
        assert ok is True, msg

    def test_invalid_timestamp_rejected(self):
        p = self._valid_payload()
        p["timestamp"] = "not-a-timestamp"
        ok, msg = EventValidator.validate_explanation_payload(p)
        assert ok is False
        assert "timestamp" in msg.lower()

    def test_session_id_empty_rejected(self):
        p = self._valid_payload()
        p["session_id"] = ""
        ok, msg = EventValidator.validate_explanation_payload(p)
        assert ok is False
        assert "session_id" in msg.lower()

    def test_non_dict_rejected(self):
        ok, msg = EventValidator.validate_explanation_payload("not a dict")  # type: ignore[arg-type]
        assert ok is False


# ─── Dispatch wiring ────────────────────────────────────────────────


class TestValidatePayloadDispatch:
    def test_explanation_dispatches_to_explanation_validator(self):
        payload = {
            "explanation_text": "x",
            "timestamp": "2026-05-03T12:00:00Z",
            "session_id": "s",
        }
        ok, _msg = EventValidator.validate_payload("EXPLANATION", payload)
        assert ok is True

    def test_explanation_no_longer_unknown(self):
        # Pre-fix: this returned (False, "Unknown event type: EXPLANATION").
        # Post-fix: it returns the explanation validator's result.
        payload = {"explanation_text": "x"}  # missing fields → False but not "unknown"
        ok, msg = EventValidator.validate_payload("EXPLANATION", payload)
        assert ok is False
        assert "Unknown event type" not in msg


# ─── log_event integration ──────────────────────────────────────────


class TestLogEventValidatesExplanation:
    @pytest.fixture
    def fresh_ledger(self, tmp_path, monkeypatch):
        from divineos.core.ledger import init_db

        db_path = tmp_path / "test_explanation.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))
        init_db()
        yield db_path

    def test_valid_explanation_logs(self, fresh_ledger):
        from divineos.core.ledger import log_event

        eid = log_event(
            "EXPLANATION",
            "assistant",
            {
                "explanation_text": "test",
                "timestamp": "2026-05-03T12:00:00Z",
                "session_id": "cli-emit",
            },
        )
        assert eid is not None

    def test_invalid_explanation_raises(self, fresh_ledger):
        from divineos.core.ledger import log_event

        with pytest.raises(ValueError, match="Invalid event payload"):
            # Missing required fields
            log_event(
                "EXPLANATION",
                "assistant",
                {"explanation_text": "test"},  # missing timestamp + session_id
            )

    def test_explanation_oversize_raises(self, fresh_ledger):
        from divineos.core.ledger import log_event

        with pytest.raises(ValueError, match="Invalid event payload"):
            log_event(
                "EXPLANATION",
                "assistant",
                {
                    "explanation_text": "x" * 1_000_001,
                    "timestamp": "2026-05-03T12:00:00Z",
                    "session_id": "cli-emit",
                },
            )

    def test_legacy_old_payload_shape_now_rejected(self, fresh_ledger):
        """Pre-fix the CLI passed {'content': content} which silently
        passed (validate=False). Post-fix that shape is rejected."""
        from divineos.core.ledger import log_event

        with pytest.raises(ValueError, match="Invalid event payload"):
            log_event(
                "EXPLANATION",
                "assistant",
                {"content": "test"},  # old shape — should fail now
            )
