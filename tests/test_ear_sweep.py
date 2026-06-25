"""Tests for divineos.core.ear_sweep — sweep stale ear_watch processes."""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.ear_sweep import SweepResult, sweep_stale_watchers


class TestSweepStaleWatchers:
    def test_no_processes_no_op(self):
        with patch("divineos.core.ear_sweep._find_ear_watch_pids", return_value=[]):
            result = sweep_stale_watchers()
            assert result.reaped == 0
            assert result.found_pids == []
            assert result.note == ""

    def test_finds_and_kills(self):
        with (
            patch("divineos.core.ear_sweep._find_ear_watch_pids", return_value=[1234, 5678]),
            patch("divineos.core.ear_sweep._kill_pid", return_value=True),
        ):
            result = sweep_stale_watchers()
            assert result.reaped == 2
            assert result.found_pids == [1234, 5678]
            assert "reaped 2 stale" in result.note

    def test_partial_kill_success(self):
        with (
            patch("divineos.core.ear_sweep._find_ear_watch_pids", return_value=[100, 200, 300]),
            patch("divineos.core.ear_sweep._kill_pid", side_effect=[True, False, True]),
        ):
            result = sweep_stale_watchers()
            assert result.reaped == 2
            assert result.found_pids == [100, 200, 300]
            assert "reaped 2 stale" in result.note

    def test_all_kills_fail_still_notes_found(self):
        with (
            patch("divineos.core.ear_sweep._find_ear_watch_pids", return_value=[100]),
            patch("divineos.core.ear_sweep._kill_pid", return_value=False),
        ):
            result = sweep_stale_watchers()
            assert result.reaped == 0
            assert result.found_pids == [100]
            assert "kill returned non-zero" in result.note


class TestSweepResultDataclass:
    def test_default_shape(self):
        r = SweepResult()
        assert r.reaped == 0
        assert r.found_pids is None
        assert r.note == ""
