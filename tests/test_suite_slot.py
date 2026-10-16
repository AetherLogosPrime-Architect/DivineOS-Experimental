"""Suites claim memory: two run together when it allows, one waits when it does not."""

from __future__ import annotations

import subprocess
import sys
import threading
import time

import pytest

from divineos.core import suite_slot
from divineos.core import system_load_check as load

GB = 1024**3


@pytest.fixture(autouse=True)
def _own_slot(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_SUITE_SLOT_DIR", str(tmp_path / "slot"))
    monkeypatch.delenv(load.SKIP_ENV_VAR, raising=False)


@pytest.fixture
def live_pids():
    """Real running processes, so a claim's owner is alive when the slot checks. Asserted live
    before use: a dead control and a blind reader return the same value."""
    procs = [
        subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"]) for _ in range(7)
    ]
    assert all(p.poll() is None for p in procs)
    yield [p.pid for p in procs]
    for p in procs:
        p.kill()
        p.wait()


def test_two_run_together_when_memory_allows(live_pids):
    a = suite_slot.try_claim(live_pids[0], cpus=4, available=100 * GB)
    b = suite_slot.try_claim(live_pids[1], cpus=4, available=100 * GB)
    assert a[0] == "go" and b[0] == "go"


def test_second_waits_when_the_first_has_claimed_what_is_left(live_pids):
    a = suite_slot.try_claim(live_pids[0], cpus=16, available=12 * GB)
    b = suite_slot.try_claim(live_pids[1], cpus=16, available=12 * GB)
    assert a[0] == "go"
    assert b[0] == "wait"
    assert str(live_pids[0]) in b[2]


def test_refused_not_queued_when_nothing_is_running_and_it_still_does_not_fit():
    verdict, flag, _ = suite_slot.try_claim(1, cpus=16, available=1 * GB)
    assert (verdict, flag) == ("refuse", None)


def test_a_claim_stops_counting_after_the_ramp(live_pids):
    t0 = time.time()
    assert suite_slot.try_claim(live_pids[0], cpus=16, available=12 * GB, now=t0)[0] == "go"
    later = t0 + suite_slot.RAMP_SECONDS + 1
    assert suite_slot.try_claim(live_pids[1], cpus=16, available=12 * GB, now=later)[0] == "go"


def test_a_dead_holders_claim_is_dropped():
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    assert suite_slot.try_claim(dead.pid, cpus=16, available=12 * GB)[0] == "go"
    me = suite_slot.try_claim(1, cpus=16, available=12 * GB)
    assert me[0] == "go"


def test_release_frees_the_memory_for_the_next(live_pids):
    suite_slot.try_claim(live_pids[0], cpus=16, available=12 * GB)
    suite_slot.release(live_pids[0])
    assert suite_slot.try_claim(live_pids[1], cpus=16, available=12 * GB)[0] == "go"


def test_seven_arrive_at_once_and_the_claims_fit_what_was_free(live_pids):
    """The crash shape. With 12 GB free only one 16-core suite fits, so exactly one gets in."""
    results: list[str] = []
    lock = threading.Lock()
    start = threading.Barrier(7)

    def go(pid: int) -> None:
        start.wait()
        got = suite_slot.try_claim(pid, cpus=16, available=12 * GB)[0]
        with lock:
            results.append(got)

    threads = [threading.Thread(target=go, args=(p,)) for p in live_pids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == ["go"] + ["wait"] * 6
