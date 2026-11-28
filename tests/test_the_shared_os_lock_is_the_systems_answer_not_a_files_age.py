"""The shared lock is the operating system's answer, never judged by a file's age."""

import os
import subprocess
import sys
import time

import pytest

from divineos.core import os_file_lock as L

HOLDER = (
    "import sys,time\n"
    "from pathlib import Path\n"
    "from divineos.core import os_file_lock as L\n"
    "fh=open(Path(sys.argv[1]),'a+b')\n"
    "assert L.try_lock(fh)\n"
    "print('held',flush=True)\n"
    "time.sleep(60)\n"
)


def _start_holder(path):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in sys.path if p)
    proc = subprocess.Popen(
        [sys.executable, "-c", HOLDER, str(path)], stdout=subprocess.PIPE, env=env, text=True
    )
    assert proc.stdout.readline().strip() == "held", "control: the holder must really be holding"
    return proc


def test_a_leftover_file_with_no_holder_does_not_block(tmp_path):
    p = tmp_path / "x.lock"
    p.write_bytes(b"leftover from a long-dead writer")
    os.utime(p, (0, 0))  # ancient: age must never matter
    assert L.is_free(p)
    with L.held(p, wait_seconds=0.5):
        pass


def test_a_really_held_lock_reads_busy_and_held_raises(tmp_path):
    p = tmp_path / "x.lock"
    proc = _start_holder(p)
    try:
        assert proc.poll() is None  # control: the holder is alive when asked
        assert not L.is_free(p)
        with pytest.raises(L.LockBusy):
            with L.held(p, wait_seconds=0.3):
                pass
    finally:
        proc.kill()
        proc.wait()


def test_the_lock_frees_the_instant_the_holder_is_killed(tmp_path):
    p = tmp_path / "x.lock"
    proc = _start_holder(p)
    proc.kill()
    proc.wait()
    deadline = time.monotonic() + 5
    while not L.is_free(p) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert L.is_free(p)


def test_is_free_releases_what_it_took(tmp_path):
    p = tmp_path / "x.lock"
    assert L.is_free(p)
    assert L.is_free(p)  # the first ask did not keep it
    with L.held(p, wait_seconds=0.5):
        pass


def test_the_lock_file_persists_after_use(tmp_path):
    p = tmp_path / "sub" / "x.lock"
    with L.held(p):
        assert p.exists()
    assert p.exists()
    assert L.is_free(p)
    assert p.exists()


def test_a_second_handle_in_this_process_reads_busy_while_held(tmp_path):
    p = tmp_path / "x.lock"
    with L.held(p):
        with open(p, "a+b") as other:
            assert L.try_lock(other) is False
    with open(p, "a+b") as other:
        assert L.try_lock(other) is True
        L.unlock(other)
