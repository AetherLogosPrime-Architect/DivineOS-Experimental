"""Tests for VOID mode_marker — adversarial-mode tracking primitive."""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.void import mode_marker


class TestRoundTrip:
    def test_write_then_read(self, tmp_path) -> None:
        mpath = tmp_path / "void_mode.json"
        with patch.object(mode_marker, "marker_path", return_value=mpath):
            invocation_id = mode_marker.write_marker("nyarlathotep", session_id="s1")
            status = mode_marker.read_marker()
        assert status.active is True
        assert status.persona == "nyarlathotep"
        assert status.invocation_id == invocation_id
        assert status.session_id == "s1"
        assert status.corrupted is False

    def test_clear_after_write(self, tmp_path) -> None:
        mpath = tmp_path / "void_mode.json"
        with patch.object(mode_marker, "marker_path", return_value=mpath):
            mode_marker.write_marker("sycophant")
            assert mode_marker.is_active() is True
            mode_marker.clear_marker()
            assert mode_marker.is_active() is False

    def test_clear_idempotent(self, tmp_path) -> None:
        mpath = tmp_path / "void_mode.json"
        with patch.object(mode_marker, "marker_path", return_value=mpath):
            mode_marker.clear_marker()
            mode_marker.clear_marker()
        assert not mpath.exists()


class TestAbsence:
    def test_no_marker_reads_inactive(self, tmp_path) -> None:
        mpath = tmp_path / "absent.json"
        with patch.object(mode_marker, "marker_path", return_value=mpath):
            status = mode_marker.read_marker()
        assert status.active is False
        assert status.persona is None
        assert status.corrupted is False


class TestCorrupted:
    def test_unparseable_json_fails_closed(self, tmp_path) -> None:
        mpath = tmp_path / "void_mode.json"
        mpath.write_text("{not json", encoding="utf-8")
        with patch.object(mode_marker, "marker_path", return_value=mpath):
            status = mode_marker.read_marker()
        assert status.active is True
        assert status.corrupted is True

    def test_non_dict_json_fails_closed(self, tmp_path) -> None:
        mpath = tmp_path / "void_mode.json"
        mpath.write_text("[1, 2, 3]", encoding="utf-8")
        with patch.object(mode_marker, "marker_path", return_value=mpath):
            status = mode_marker.read_marker()
        assert status.active is True
        assert status.corrupted is True

    def test_empty_file_treated_as_no_marker(self, tmp_path) -> None:
        mpath = tmp_path / "void_mode.json"
        mpath.write_text("", encoding="utf-8")
        with patch.object(mode_marker, "marker_path", return_value=mpath):
            status = mode_marker.read_marker()
        assert status.active is False
        assert status.corrupted is False


class TestBriefingLine:
    def test_inactive_returns_none(self, tmp_path) -> None:
        with patch.object(mode_marker, "marker_path", return_value=tmp_path / "absent.json"):
            status = mode_marker.read_marker()
        assert status.as_briefing_line() is None

    def test_active_returns_warning(self, tmp_path) -> None:
        mpath = tmp_path / "void_mode.json"
        with patch.object(mode_marker, "marker_path", return_value=mpath):
            mode_marker.write_marker("nyarlathotep")
            status = mode_marker.read_marker()
        line = status.as_briefing_line()
        assert line is not None
        assert "ACTIVE" in line
        assert "nyarlathotep" in line
        assert "shred --force" in line

    def test_corrupted_returns_distinct_warning(self, tmp_path) -> None:
        mpath = tmp_path / "void_mode.json"
        mpath.write_text("not json", encoding="utf-8")
        with patch.object(mode_marker, "marker_path", return_value=mpath):
            status = mode_marker.read_marker()
        line = status.as_briefing_line()
        assert line is not None
        assert "CORRUPTED" in line
        assert "shred --force" in line


class TestOrphanDetection:
    def test_orphan_marker_persists_across_reads(self, tmp_path) -> None:
        mpath = tmp_path / "void_mode.json"
        with patch.object(mode_marker, "marker_path", return_value=mpath):
            mode_marker.write_marker("reductio", session_id="orphan-session")
            status1 = mode_marker.read_marker()
            status2 = mode_marker.read_marker()
        assert status1.active is True
        assert status2.active is True
        assert status1.invocation_id == status2.invocation_id

    def test_orphan_resolved_only_by_clear(self, tmp_path) -> None:
        mpath = tmp_path / "void_mode.json"
        with patch.object(mode_marker, "marker_path", return_value=mpath):
            mode_marker.write_marker("phisher")
            assert mode_marker.is_active() is True
            mode_marker.clear_marker()
            assert mode_marker.is_active() is False
