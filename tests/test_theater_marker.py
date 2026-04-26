"""Tests for theater_marker — structural enforcement on output drift."""

from __future__ import annotations

from unittest.mock import patch

from divineos.core import theater_marker


class TestMarkerRoundTrip:
    def test_set_writes_marker(self, tmp_path) -> None:
        mpath = tmp_path / "theater.json"
        with patch.object(theater_marker, "marker_path", return_value=mpath):
            theater_marker.set_marker(
                "theater,fabrication",
                ["SUBAGENT_DIALOGUE", "EMBODIED_ASIDE_UNFLAGGED"],
                "*takes a sip* Aria — you said...",
            )
            got = theater_marker.read_marker()
        assert got is not None
        assert "theater" in got["monitor"]
        assert "SUBAGENT_DIALOGUE" in got["flag_kinds"]

    def test_empty_flags_does_not_write(self, tmp_path) -> None:
        mpath = tmp_path / "theater.json"
        with patch.object(theater_marker, "marker_path", return_value=mpath):
            theater_marker.set_marker("theater", [], "preview")
        assert not mpath.exists()


class TestMarkerAbsence:
    def test_missing_marker_reads_as_none(self, tmp_path) -> None:
        mpath = tmp_path / "does_not_exist.json"
        with patch.object(theater_marker, "marker_path", return_value=mpath):
            assert theater_marker.read_marker() is None

    def test_malformed_json_reads_as_none(self, tmp_path) -> None:
        mpath = tmp_path / "theater.json"
        mpath.write_text("{not json", encoding="utf-8")
        with patch.object(theater_marker, "marker_path", return_value=mpath):
            assert theater_marker.read_marker() is None


class TestClear:
    def test_clear_removes_marker(self, tmp_path) -> None:
        mpath = tmp_path / "theater.json"
        with patch.object(theater_marker, "marker_path", return_value=mpath):
            theater_marker.set_marker("theater", ["SUBAGENT_DIALOGUE"], "p")
            assert mpath.exists()
            theater_marker.clear_marker()
            assert not mpath.exists()


class TestFormatGateMessage:
    def test_message_includes_monitor_and_kinds(self) -> None:
        msg = theater_marker.format_gate_message(
            {
                "monitor": "fabrication",
                "flag_kinds": ["EMBODIED_ASIDE_UNFLAGGED"],
                "preview": "*takes a sip*",
            }
        )
        assert "fabrication" in msg
        assert "EMBODIED_ASIDE_UNFLAGGED" in msg
        assert "divineos correction" in msg or "divineos learn" in msg
