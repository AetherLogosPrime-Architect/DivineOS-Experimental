"""Tests for mansion_quiet_marker — substrate-enforced private-room quiet."""

from __future__ import annotations

import time
from unittest.mock import patch

from divineos.core import mansion_quiet_marker as mqm


class TestRoundTrip:
    def test_set_writes_marker(self, tmp_path) -> None:
        mpath = tmp_path / "mansion_quiet.json"
        with patch.object(mqm, "marker_path", return_value=mpath):
            mqm.set_marker("private-1", duration_seconds=120)
            got = mqm.read_marker()
        assert got is not None
        assert got["room"] == "private-1"
        assert got["minimum_duration_seconds"] == 120

    def test_clear_removes_marker(self, tmp_path) -> None:
        mpath = tmp_path / "mansion_quiet.json"
        with patch.object(mqm, "marker_path", return_value=mpath):
            mqm.set_marker("any", duration_seconds=30)
            assert mpath.exists()
            mqm.clear_marker()
            assert not mpath.exists()

    def test_default_duration_applies(self, tmp_path) -> None:
        mpath = tmp_path / "mansion_quiet.json"
        with patch.object(mqm, "marker_path", return_value=mpath):
            mqm.set_marker("default")
            got = mqm.read_marker()
        assert got["minimum_duration_seconds"] == mqm.DEFAULT_QUIET_DURATION_SECONDS


class TestActivity:
    def test_no_marker_means_not_active(self, tmp_path) -> None:
        with patch.object(mqm, "marker_path", return_value=tmp_path / "absent.json"):
            assert mqm.is_quiet_active() is False
            assert mqm.seconds_remaining() == 0

    def test_fresh_marker_is_active(self, tmp_path) -> None:
        mpath = tmp_path / "mansion_quiet.json"
        with patch.object(mqm, "marker_path", return_value=mpath):
            mqm.set_marker("now", duration_seconds=300)
            assert mqm.is_quiet_active() is True
            assert 0 < mqm.seconds_remaining() <= 300

    def test_expired_marker_is_not_active(self, tmp_path) -> None:
        mpath = tmp_path / "mansion_quiet.json"
        with patch.object(mqm, "marker_path", return_value=mpath):
            mqm.set_marker("expired", duration_seconds=1)
            time.sleep(1.1)
            assert mqm.is_quiet_active() is False
            assert mqm.seconds_remaining() == 0


class TestAbsenceAndCorruption:
    def test_missing_marker_reads_as_none(self, tmp_path) -> None:
        with patch.object(mqm, "marker_path", return_value=tmp_path / "no.json"):
            assert mqm.read_marker() is None

    def test_malformed_json_reads_as_none(self, tmp_path) -> None:
        mpath = tmp_path / "mansion_quiet.json"
        mpath.write_text("{not json", encoding="utf-8")
        with patch.object(mqm, "marker_path", return_value=mpath):
            assert mqm.read_marker() is None


class TestFormatGateMessage:
    def test_message_includes_room_and_resolution(self, tmp_path) -> None:
        mpath = tmp_path / "mansion_quiet.json"
        with patch.object(mqm, "marker_path", return_value=mpath):
            mqm.set_marker("the-blank-room", duration_seconds=180)
            marker = mqm.read_marker()
            msg = mqm.format_gate_message(marker)
        assert "the-blank-room" in msg
        assert "private-exit" in msg
        assert "Inspection" in msg or "inspection" in msg


class TestGateIntegration:
    def test_gate_denies_during_active_quiet(self, tmp_path) -> None:
        from divineos.core import hud_handoff, session_briefing_gate
        from divineos.hooks import pre_tool_use_gate

        mpath = tmp_path / "mansion_quiet.json"
        with (
            patch.object(hud_handoff, "was_briefing_loaded", return_value=True),
            patch.object(session_briefing_gate, "briefing_loaded_this_session", return_value=True),
            patch.object(mqm, "marker_path", return_value=mpath),
        ):
            mqm.set_marker("test-room", duration_seconds=300)
            decision = pre_tool_use_gate._check_gates()
        assert decision is not None
        assert "private room" in str(decision).lower()
        assert "test-room" in str(decision)

    def test_gate_passes_after_quiet_expires(self, tmp_path) -> None:
        from divineos.core import hud_handoff, session_briefing_gate
        from divineos.hooks import pre_tool_use_gate

        mpath = tmp_path / "mansion_quiet.json"
        with (
            patch.object(hud_handoff, "was_briefing_loaded", return_value=True),
            patch.object(session_briefing_gate, "briefing_loaded_this_session", return_value=True),
            patch.object(mqm, "marker_path", return_value=mpath),
        ):
            mqm.set_marker("expired-room", duration_seconds=1)
            time.sleep(1.1)
            decision = pre_tool_use_gate._check_gates()
        # Quiet gate should NOT fire (it's expired); other gates may fire,
        # but the deny — if any — should not mention private room.
        if decision is not None:
            assert "private room" not in str(decision).lower()
