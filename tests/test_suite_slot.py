"""Only one holder of the suite slot at a time; a dead holder cannot keep it."""

from __future__ import annotations

import os
import subprocess
import sys
import threading

import pytest

from divineos.core import suite_slot


@pytest.fixture(autouse=True)
def _own_slot(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_SUITE_SLOT_DIR", str(tmp_path / "slot.lock"))


def test_second_taker_is_refused_while_first_is_alive():
    me = os.getpid()
    assert suite_slot.try_acquire(me)
    assert not suite_slot.try_acquire(me + 1_000_000)


def test_release_lets_the_next_in():
    me = os.getpid()
    assert suite_slot.try_acquire(me)
    suite_slot.release(me)
    assert suite_slot.try_acquire(me)


def test_only_the_owner_can_release():
    me = os.getpid()
    assert suite_slot.try_acquire(me)
    suite_slot.release(me + 1)
    assert not suite_slot.try_acquire(me + 2)


def test_a_dead_holder_is_taken_over():
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    assert suite_slot.try_acquire(dead.pid)
    assert suite_slot.try_acquire(os.getpid())


def test_seven_arrive_at_once_exactly_one_wins():
    """The crash shape: seven arrive together. The winner must be a live pid, else a later
    taker would legitimately take over and the count would not mean what it says."""
    me = os.getpid()
    results: list[bool] = []
    start = threading.Barrier(7)
    lock = threading.Lock()

    def go(n: int) -> None:
        start.wait()
        got = suite_slot.try_acquire(me)
        with lock:
            results.append(got)

    threads = [threading.Thread(target=go, args=(n,)) for n in range(7)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 7
    assert sum(results) == 1
