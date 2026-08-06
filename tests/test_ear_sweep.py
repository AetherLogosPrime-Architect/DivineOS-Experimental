"""Tests for divineos.core.ear_sweep — sweep stale ear_watch processes."""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.ear_sweep import SweepResult, sweep_stale_watchers


class TestSweepStaleWatchers:
    def test_no_processes_says_it_ran(self):
        """A clean sweep must SAY it swept.

        This asserted ``note == ""`` until 2026-08-06. The code was changed
        deliberately to speak on the success path, with the reason in its own
        comment: a clean run that printed nothing made "found nothing",
        "crashed", and "never ran" three states that looked identical from
        outside. The ScanUnavailable branch had already been fixed for exactly
        that ambiguity; it survived on the success path where nobody looked.

        So the code is right and the expectation was stale. Asserting silence
        here would have re-armed the defect the change exists to kill.
        """
        with patch("divineos.core.ear_sweep._find_ear_watch_pids", return_value=[]):
            result = sweep_stale_watchers()
            assert result.reaped == 0
            assert result.found_pids == []
            assert "no orphaned watchers" in result.note
            assert result.note != "", "a clean run must be distinguishable from a run that never happened"

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
