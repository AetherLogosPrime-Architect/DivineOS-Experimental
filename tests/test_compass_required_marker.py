"""Tests for compass_required_marker — virtue-relevant event gate."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from divineos.core import compass_required_marker


@pytest.fixture
def allow_cascade(monkeypatch):
    """Opt the test into actually firing the cascade.

    set_marker no-ops under pytest by default to avoid leaking markers
    from one test into another / into the user's environment. Tests
    that genuinely need the cascade fire opt in via this fixture.
    """
    monkeypatch.setenv("DIVINEOS_TEST_ALLOW_COMPASS_CASCADE", "1")


class TestRoundTrip:
    def test_set_writes_marker(self, tmp_path, allow_cascade) -> None:
        mpath = tmp_path / "compass_required.json"
        with patch.object(compass_required_marker, "marker_path", return_value=mpath):
            compass_required_marker.set_marker("correction", "you missed something")
            got = compass_required_marker.read_marker()
        assert got is not None
        assert got["kind"] == "correction"
        assert "you missed" in got["summary"]

    def test_set_truncates_summary_to_200_chars(self, tmp_path, allow_cascade) -> None:
        mpath = tmp_path / "compass_required.json"
        long = "y" * 500
        with patch.object(compass_required_marker, "marker_path", return_value=mpath):
            compass_required_marker.set_marker("correction", long)
            got = compass_required_marker.read_marker()
        assert len(got["summary"]) == 200

    def test_clear_removes_marker(self, tmp_path, allow_cascade) -> None:
        mpath = tmp_path / "compass_required.json"
        with patch.object(compass_required_marker, "marker_path", return_value=mpath):
            compass_required_marker.set_marker("hedge", "x")
            assert mpath.exists()
            compass_required_marker.clear_marker()
            assert not mpath.exists()


class TestPytestNoOp:
    def test_set_marker_noops_under_pytest_by_default(self, tmp_path) -> None:
        """Without the opt-in env, set_marker is a no-op when pytest is running."""
        mpath = tmp_path / "compass_required.json"
        # Ensure the opt-in is NOT set.
        prev = os.environ.pop("DIVINEOS_TEST_ALLOW_COMPASS_CASCADE", None)
        try:
            with patch.object(compass_required_marker, "marker_path", return_value=mpath):
                compass_required_marker.set_marker("correction", "trigger text")
        finally:
            if prev is not None:
                os.environ["DIVINEOS_TEST_ALLOW_COMPASS_CASCADE"] = prev
        assert not mpath.exists()


class TestAbsence:
    def test_missing_marker_reads_as_none(self, tmp_path) -> None:
        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "nope.json"
        ):
            assert compass_required_marker.read_marker() is None

    def test_malformed_json_reads_as_none(self, tmp_path) -> None:
        mpath = tmp_path / "compass_required.json"
        mpath.write_text("{not json", encoding="utf-8")
        with patch.object(compass_required_marker, "marker_path", return_value=mpath):
            assert compass_required_marker.read_marker() is None


class TestFormatGateMessage:
    def test_message_includes_kind_and_command(self) -> None:
        msg = compass_required_marker.format_gate_message(
            {"kind": "correction", "summary": "you missed it"}
        )
        assert "correction" in msg
        assert "compass-ops observe" in msg
