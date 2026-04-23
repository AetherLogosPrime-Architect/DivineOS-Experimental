"""Tests for hedge_marker — structural enforcement of claim-filing on hedging."""

from __future__ import annotations

import json
from unittest.mock import patch

from divineos.core import hedge_marker


class TestMarkerRoundTrip:
    def test_set_above_threshold_writes_marker(self, tmp_path) -> None:
        mpath = tmp_path / "hedge.json"
        with patch.object(hedge_marker, "marker_path", return_value=mpath):
            hedge_marker.set_marker(3, ["RECYCLING", "EPISTEMIC_COLLAPSE"], "preview text")
            got = hedge_marker.read_marker()
        assert got is not None
        assert got["flag_count"] == 3
        assert "RECYCLING" in got["flag_kinds"]

    def test_set_below_threshold_does_not_write(self, tmp_path) -> None:
        mpath = tmp_path / "hedge.json"
        with patch.object(hedge_marker, "marker_path", return_value=mpath):
            hedge_marker.set_marker(1, ["RECYCLING"], "preview")
        assert not mpath.exists()


class TestMarkerAbsence:
    def test_missing_marker_reads_as_none(self, tmp_path) -> None:
        mpath = tmp_path / "does_not_exist.json"
        with patch.object(hedge_marker, "marker_path", return_value=mpath):
            assert hedge_marker.read_marker() is None

    def test_malformed_json_reads_as_none(self, tmp_path) -> None:
        mpath = tmp_path / "hedge.json"
        mpath.write_text("{not json", encoding="utf-8")
        with patch.object(hedge_marker, "marker_path", return_value=mpath):
            assert hedge_marker.read_marker() is None


class TestClear:
    def test_clear_removes_marker(self, tmp_path) -> None:
        mpath = tmp_path / "hedge.json"
        mpath.write_text(
            json.dumps({"ts": 1.0, "flag_count": 2, "flag_kinds": ["X"], "preview": "p"}),
            encoding="utf-8",
        )
        with patch.object(hedge_marker, "marker_path", return_value=mpath):
            assert hedge_marker.read_marker() is not None
            hedge_marker.clear_marker()
            assert hedge_marker.read_marker() is None


class TestGateIntegration:
    def test_gate_denies_when_marker_present(self, tmp_path) -> None:
        from divineos.core import hud_handoff
        from divineos.hooks import pre_tool_use_gate

        mpath = tmp_path / "hedge.json"
        mpath.write_text(
            json.dumps(
                {
                    "ts": 1.0,
                    "flag_count": 3,
                    "flag_kinds": ["RECYCLING"],
                    "preview": "maybe it works, probably fine, could be",
                }
            ),
            encoding="utf-8",
        )
        with (
            patch.object(hud_handoff, "was_briefing_loaded", return_value=True),
            patch.object(hedge_marker, "marker_path", return_value=mpath),
        ):
            decision = pre_tool_use_gate._check_gates()
        assert decision is not None
        assert "hedge" in str(decision).lower()
        assert "divineos claim" in str(decision)


class TestGateMessage:
    def test_message_includes_count_and_preview(self) -> None:
        msg = hedge_marker.format_gate_message(
            {"flag_count": 4, "flag_kinds": ["A", "B"], "preview": "uncertain text"}
        )
        assert "4 hedge flag" in msg
        assert "uncertain text" in msg
        assert "divineos claim" in msg
