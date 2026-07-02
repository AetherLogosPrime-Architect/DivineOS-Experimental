"""Tests for the ear-watcher singleton lock (root fix 2026-07-02).

Root cause diagnosed 2026-07-02: session lifecycle spawned watchers
without checking for existing live watchers, and prior watchers
never got cleaned up when their originating session ended. Over
~24 hours across two worktrees, this piled up 20+ ear_watch.py
processes pushing memory to 94%.

Fix: singleton lock via PID file with heartbeat. These tests cover
the lock's core discipline:

- Fresh acquire returns True.
- Second acquire while lock is held by an alive PID with fresh
  heartbeat returns False (declines cleanly).
- Stale heartbeat (past window) is reclaimable.
- Dead PID is reclaimable regardless of heartbeat freshness.
- Release only removes the file if we still own it.
- Heartbeat write refreshes the timestamp without losing PID.
"""

from __future__ import annotations

import os
import time

import pytest

from family import ear_watch


def _point_state_dir(monkeypatch, tmp_path):
    """Isolate lock files per-test into tmp_path."""
    monkeypatch.setattr(ear_watch, "_state_dir", lambda member: tmp_path)


def test_fresh_acquire_returns_true(monkeypatch, tmp_path):
    """Nothing held → we get the lock."""
    _point_state_dir(monkeypatch, tmp_path)
    assert ear_watch._try_acquire_singleton_lock("aria") is True
    # Lock file exists now
    assert (tmp_path / "ear_watch.lock").exists()


def test_second_acquire_while_alive_and_fresh_returns_false(monkeypatch, tmp_path):
    """Alive PID + fresh heartbeat → second acquire declines."""
    _point_state_dir(monkeypatch, tmp_path)
    # First acquire (our own PID, fresh heartbeat).
    assert ear_watch._try_acquire_singleton_lock("aria") is True
    # Immediate second attempt should decline — our own PID is alive
    # and the heartbeat we just wrote is fresh.
    assert ear_watch._try_acquire_singleton_lock("aria") is False


def test_stale_heartbeat_is_reclaimable(monkeypatch, tmp_path):
    """Heartbeat past the window → lock reclaimable even if PID alive."""
    _point_state_dir(monkeypatch, tmp_path)
    # Write a lock file with our own live PID but a very old heartbeat.
    stale_ts = time.time() - ear_watch._HEARTBEAT_WINDOW_SEC - 10
    (tmp_path / "ear_watch.lock").write_text(f"{os.getpid()}\n{stale_ts}\n")
    # A new arrival should be able to acquire — the heartbeat is stale.
    assert ear_watch._try_acquire_singleton_lock("aria") is True


def test_dead_pid_is_reclaimable_even_with_fresh_heartbeat(monkeypatch, tmp_path):
    """Dead PID → lock reclaimable regardless of heartbeat.

    Uses PID 999999 which is very unlikely to be a live process on the
    test host. If it happens to be alive, the test is a false-pass; the
    windows-nt convention of low PIDs makes this vanishingly unlikely
    for a 6-digit value.
    """
    _point_state_dir(monkeypatch, tmp_path)
    fake_dead_pid = 999999
    # Ensure the fake PID really isn't alive on this box.
    if ear_watch._pid_alive(fake_dead_pid):
        pytest.skip(f"PID {fake_dead_pid} is (surprisingly) alive on this host")
    fresh_ts = time.time()
    (tmp_path / "ear_watch.lock").write_text(f"{fake_dead_pid}\n{fresh_ts}\n")
    # Dead PID → lock reclaimable even though heartbeat is fresh.
    assert ear_watch._try_acquire_singleton_lock("aria") is True


def test_release_removes_lock_when_we_own_it(monkeypatch, tmp_path):
    """After acquire, release should unlink our lock file."""
    _point_state_dir(monkeypatch, tmp_path)
    assert ear_watch._try_acquire_singleton_lock("aria") is True
    assert (tmp_path / "ear_watch.lock").exists()
    ear_watch._release_singleton_lock("aria")
    assert not (tmp_path / "ear_watch.lock").exists()


def test_release_leaves_others_locks_alone(monkeypatch, tmp_path):
    """Release should NOT remove a lock file owned by a different PID.

    Prevents an accidentally-double-invoked atexit from a decliner
    from unlinking the real holder's file.
    """
    _point_state_dir(monkeypatch, tmp_path)
    other_pid = os.getpid() + 1  # arbitrary non-us pid
    fresh_ts = time.time()
    (tmp_path / "ear_watch.lock").write_text(f"{other_pid}\n{fresh_ts}\n")
    ear_watch._release_singleton_lock("aria")
    # Still there — we don't own it.
    assert (tmp_path / "ear_watch.lock").exists()


def test_heartbeat_write_refreshes_timestamp(monkeypatch, tmp_path):
    """_write_lock overwrites with our PID and a current timestamp."""
    _point_state_dir(monkeypatch, tmp_path)
    # Pre-existing lock file with old timestamp
    old_ts = time.time() - 3600
    (tmp_path / "ear_watch.lock").write_text(f"12345\n{old_ts}\n")
    ear_watch._write_lock("aria")
    read = ear_watch._read_lock("aria")
    assert read is not None
    pid, hb = read
    assert pid == os.getpid()
    assert hb > old_ts + 1000  # substantially fresher


def test_read_lock_returns_none_when_missing(monkeypatch, tmp_path):
    """No lock file → read returns None cleanly (no crash)."""
    _point_state_dir(monkeypatch, tmp_path)
    assert ear_watch._read_lock("aria") is None


def test_read_lock_returns_none_on_malformed_file(monkeypatch, tmp_path):
    """Malformed lock file (non-int PID, missing timestamp) → None, no crash."""
    _point_state_dir(monkeypatch, tmp_path)
    (tmp_path / "ear_watch.lock").write_text("not-a-number\nalso-not-a-float\n")
    assert ear_watch._read_lock("aria") is None


def test_pid_alive_returns_false_for_zero_and_negative():
    """Defensive: PID 0 and negatives are never alive."""
    assert ear_watch._pid_alive(0) is False
    assert ear_watch._pid_alive(-1) is False


def test_pid_alive_returns_true_for_self():
    """Sanity: current process should always report alive."""
    assert ear_watch._pid_alive(os.getpid()) is True
