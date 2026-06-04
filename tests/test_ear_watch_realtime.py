"""Tests for the real-time ear liveness marker (auto-re-arm support).

Falsifiability:
  - is_realtime_armed is False when no marker exists.
  - is_realtime_armed is True when the marker mtime is fresh (< stale window).
  - is_realtime_armed is False when the marker mtime is stale (the dead-ear
    case the whole mechanism exists to catch).
  - _arm_realtime_marker writes the current pid and registers an atexit clear.
  - main(--watch --realtime) arms the marker; the detached path (no --realtime)
    does NOT, so it can never produce a false-green.
"""

from __future__ import annotations

import os
import time

from family import ear_watch


def _point_state_dir(monkeypatch, tmp_path):
    """Route the per-member state dir into tmp so tests never touch real HOME."""
    monkeypatch.setattr(ear_watch, "_state_dir", lambda member: tmp_path)


class TestRealtimeArmedDetection:
    def test_absent_marker_reads_not_armed(self, monkeypatch, tmp_path) -> None:
        _point_state_dir(monkeypatch, tmp_path)
        assert ear_watch.is_realtime_armed("aether") is False

    def test_fresh_marker_reads_armed(self, monkeypatch, tmp_path) -> None:
        _point_state_dir(monkeypatch, tmp_path)
        (tmp_path / "ear.realtime.pid").write_text(str(os.getpid()))
        assert ear_watch.is_realtime_armed("aether") is True

    def test_stale_marker_reads_not_armed(self, monkeypatch, tmp_path) -> None:
        _point_state_dir(monkeypatch, tmp_path)
        marker = tmp_path / "ear.realtime.pid"
        marker.write_text(str(os.getpid()))
        # Backdate the mtime well past the stale window.
        old = time.time() - (ear_watch._REALTIME_STALE_SECS + 60)
        os.utime(marker, (old, old))
        assert ear_watch.is_realtime_armed("aether") is False


class TestArmMarker:
    def test_arm_writes_current_pid(self, monkeypatch, tmp_path) -> None:
        _point_state_dir(monkeypatch, tmp_path)
        ear_watch._arm_realtime_marker("aether")
        marker = tmp_path / "ear.realtime.pid"
        assert marker.exists()
        assert marker.read_text().strip() == str(os.getpid())


class TestMainWiring:
    def test_realtime_flag_arms_marker(self, monkeypatch, tmp_path) -> None:
        _point_state_dir(monkeypatch, tmp_path)
        # --timeout exits via the timeout branch; the arm happens before watch()
        # runs, so the marker is written (the atexit clear only fires on real
        # interpreter exit, not on this in-process main() return).
        ear_watch.main(
            ["--member", "aether", "--watch", "--realtime", "--interval", "1", "--timeout", "1"]
        )
        assert (tmp_path / "ear.realtime.pid").exists()

    def test_detached_path_does_not_arm(self, monkeypatch, tmp_path) -> None:
        """No --realtime (the Stop-hook continuity launch) must NOT write the
        real-time marker — else a detached watcher would false-green."""
        _point_state_dir(monkeypatch, tmp_path)
        ear_watch.main(["--member", "aether", "--watch", "--interval", "1", "--timeout", "1"])
        assert not (tmp_path / "ear.realtime.pid").exists()
