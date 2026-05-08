"""Tests for session_briefing_gate — per-session briefing-loaded enforcement.

The gate now reads the ``.briefing_loaded`` marker file (written by
``mark_briefing_loaded()``) and verifies its session_id matches the
current session. Tests use ``tmp_path`` with monkeypatched HUD-dir
resolution to avoid touching real on-disk markers.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from divineos.core import session_briefing_gate


@pytest.fixture
def isolated_hud_dir(monkeypatch, tmp_path):
    """Patch _get_hud_dir so the gate reads from a temp directory."""
    hud_dir = tmp_path / "hud"
    hud_dir.mkdir()

    def _fake_get_hud_dir() -> Path:
        return hud_dir

    monkeypatch.setattr("divineos.core._hud_io._get_hud_dir", _fake_get_hud_dir)
    return hud_dir


def _write_marker(hud_dir: Path, session_id: str | None) -> None:
    marker: dict[str, object] = {"loaded_at": 1234567890, "tool_calls_at_load": 0}
    if session_id is not None:
        marker["session_id"] = session_id
    (hud_dir / ".briefing_loaded").write_text(json.dumps(marker), encoding="utf-8")


class TestBriefingLoadedThisSession:
    def test_returns_true_when_marker_session_matches(self, isolated_hud_dir) -> None:
        sid = "session-abc-123"
        _write_marker(isolated_hud_dir, sid)
        with patch(
            "divineos.core.session_manager.get_current_session_id",
            return_value=sid,
        ):
            assert session_briefing_gate.briefing_loaded_this_session() is True

    def test_returns_false_when_marker_for_other_session(self, isolated_hud_dir) -> None:
        _write_marker(isolated_hud_dir, "other-session")
        with patch(
            "divineos.core.session_manager.get_current_session_id",
            return_value="my-session",
        ):
            assert session_briefing_gate.briefing_loaded_this_session() is False

    def test_returns_false_when_no_marker_present(self, isolated_hud_dir) -> None:
        with patch(
            "divineos.core.session_manager.get_current_session_id",
            return_value="my-session",
        ):
            assert session_briefing_gate.briefing_loaded_this_session() is False

    def test_fails_open_when_session_manager_raises(self, isolated_hud_dir) -> None:
        with patch(
            "divineos.core.session_manager.get_current_session_id",
            side_effect=RuntimeError("no session"),
        ):
            assert session_briefing_gate.briefing_loaded_this_session() is True

    def test_fails_open_when_marker_unreadable(self, isolated_hud_dir) -> None:
        (isolated_hud_dir / ".briefing_loaded").write_text("not-json", encoding="utf-8")
        with patch(
            "divineos.core.session_manager.get_current_session_id",
            return_value="my-session",
        ):
            assert session_briefing_gate.briefing_loaded_this_session() is True

    def test_returns_false_when_marker_lacks_session_id(self, isolated_hud_dir) -> None:
        _write_marker(isolated_hud_dir, None)
        with patch(
            "divineos.core.session_manager.get_current_session_id",
            return_value="my-session",
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
