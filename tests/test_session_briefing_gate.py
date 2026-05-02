"""Tests for session_briefing_gate — per-session BRIEFING_LOADED enforcement."""

from __future__ import annotations

from unittest.mock import patch

from divineos.core import session_briefing_gate


class TestBriefingLoadedThisSession:
    def test_returns_true_when_event_matches_current_session(self) -> None:
        sid = "session-abc-123"
        events = [
            {"event_type": "BRIEFING_LOADED", "session_id": sid},
            {"event_type": "TOOL_CALL", "session_id": sid},
        ]
        with (
            patch.object(session_briefing_gate, "__name__", session_briefing_gate.__name__),
            patch(
                "divineos.core.session_manager.get_current_session_id",
                return_value=sid,
            ),
            patch("divineos.core.ledger.search_events", return_value=events),
        ):
            assert session_briefing_gate.briefing_loaded_this_session() is True

    def test_returns_false_when_event_only_for_other_session(self) -> None:
        events = [
            {"event_type": "BRIEFING_LOADED", "session_id": "other-session"},
        ]
        with (
            patch(
                "divineos.core.session_manager.get_current_session_id",
                return_value="my-session",
            ),
            patch("divineos.core.ledger.search_events", return_value=events),
        ):
            assert session_briefing_gate.briefing_loaded_this_session() is False

    def test_returns_false_when_no_briefing_event_for_session(self) -> None:
        events: list[dict] = []
        with (
            patch(
                "divineos.core.session_manager.get_current_session_id",
                return_value="my-session",
            ),
            patch("divineos.core.ledger.search_events", return_value=events),
        ):
            assert session_briefing_gate.briefing_loaded_this_session() is False

    def test_fails_open_when_session_manager_raises(self) -> None:
        with patch(
            "divineos.core.session_manager.get_current_session_id",
            side_effect=RuntimeError("no session"),
        ):
            assert session_briefing_gate.briefing_loaded_this_session() is True

    def test_fails_open_when_ledger_raises(self) -> None:
        with (
            patch(
                "divineos.core.session_manager.get_current_session_id",
                return_value="my-session",
            ),
            patch(
                "divineos.core.ledger.search_events",
                side_effect=OSError("db unavailable"),
            ),
        ):
            assert session_briefing_gate.briefing_loaded_this_session() is True

    def test_ignores_non_briefing_events_for_session(self) -> None:
        events = [
            {"event_type": "TOOL_CALL", "session_id": "my-session"},
            {"event_type": "GOAL_ADDED", "session_id": "my-session"},
        ]
        with (
            patch(
                "divineos.core.session_manager.get_current_session_id",
                return_value="my-session",
            ),
            patch("divineos.core.ledger.search_events", return_value=events),
        ):
            assert session_briefing_gate.briefing_loaded_this_session() is False


class TestGateMessage:
    def test_message_names_session_and_command(self) -> None:
        msg = session_briefing_gate.gate_message()
        assert "this session" in msg.lower() or "THIS session" in msg
        assert "divineos briefing" in msg

    def test_status_reports_blocking_state(self) -> None:
        with patch.object(
            session_briefing_gate, "briefing_loaded_this_session", return_value=False
        ):
            status = session_briefing_gate.gate_status()
        assert status["loaded_this_session"] is False
        assert status["blocks"] is True
