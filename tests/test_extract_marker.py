"""Tests for extract_marker — trigger-attributed extract idempotency marker.

Falsifiability:
  - Round-trip: write_marker then read_marker preserves trigger.
  - Legacy "1" content reads as trigger="unknown".
  - Malformed JSON reads as trigger="unknown".
  - Missing marker reads as None.
  - format_skip_message always includes the trigger verbatim.
"""

from __future__ import annotations

import time
from unittest.mock import patch

from divineos.core import extract_marker


class TestRoundTrip:
    def test_write_and_read_preserves_trigger(self, tmp_path) -> None:
        mpath = tmp_path / "marker"
        with patch.object(extract_marker, "marker_path", return_value=mpath):
            extract_marker.write_marker(trigger="sleep", session_id="abc")
            got = extract_marker.read_marker()
        assert got is not None
        assert got["trigger"] == "sleep"
        assert got["session_id"] == "abc"
        assert isinstance(got["ts"], float)

    def test_default_trigger_is_manual(self, tmp_path) -> None:
        mpath = tmp_path / "marker"
        with patch.object(extract_marker, "marker_path", return_value=mpath):
            extract_marker.write_marker()
            got = extract_marker.read_marker()
        assert got["trigger"] == "manual"


class TestLegacyCompat:
    def test_legacy_literal_one_reads_as_unknown(self, tmp_path) -> None:
        mpath = tmp_path / "marker"
        mpath.write_text("1", encoding="utf-8")
        with patch.object(extract_marker, "marker_path", return_value=mpath):
            got = extract_marker.read_marker()
        assert got == {"trigger": "unknown"}

    def test_malformed_json_reads_as_unknown(self, tmp_path) -> None:
        mpath = tmp_path / "marker"
        mpath.write_text("{not json", encoding="utf-8")
        with patch.object(extract_marker, "marker_path", return_value=mpath):
            got = extract_marker.read_marker()
        assert got == {"trigger": "unknown"}

    def test_empty_content_reads_as_unknown(self, tmp_path) -> None:
        mpath = tmp_path / "marker"
        mpath.write_text("", encoding="utf-8")
        with patch.object(extract_marker, "marker_path", return_value=mpath):
            got = extract_marker.read_marker()
        assert got == {"trigger": "unknown"}

    def test_missing_marker_reads_as_none(self, tmp_path) -> None:
        mpath = tmp_path / "does_not_exist"
        with patch.object(extract_marker, "marker_path", return_value=mpath):
            got = extract_marker.read_marker()
        assert got is None


class TestFormatSkipMessage:
    def test_includes_trigger(self) -> None:
        msg = extract_marker.format_skip_message({"trigger": "sleep", "ts": time.time()})
        assert "sleep" in msg

    def test_seconds_format_under_a_minute(self) -> None:
        msg = extract_marker.format_skip_message({"trigger": "manual", "ts": time.time() - 15})
        assert "15s ago" in msg

    def test_minutes_format_under_an_hour(self) -> None:
        msg = extract_marker.format_skip_message({"trigger": "manual", "ts": time.time() - 600})
        assert "10m ago" in msg

    def test_missing_ts_omits_age(self) -> None:
        msg = extract_marker.format_skip_message({"trigger": "unknown"})
        assert "unknown" in msg
        assert "ago" not in msg
