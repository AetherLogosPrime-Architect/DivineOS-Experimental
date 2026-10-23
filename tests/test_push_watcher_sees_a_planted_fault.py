"""The real sampler, against a real killed worker and against its absence.

Turing's finding (walk-193e1c70464f): a watcher that works and one that merely runs return the same value on a quiet
push, so the only proof is to plant the fault AND its absence. The first test kills a helper on purpose while its
parent and its sibling keep running and asserts the report names it. The second runs the identical setup with no kill
and asserts the report names nothing. If either passes while the watcher is blind, the other fails.

The stand-in "workers" carry the signature in their command line, which is all the sampler keys on. They are real
processes; nothing here imitates a process table.

WHAT THIS DOES NOT COVER: Windows' own way of ending a worker (a job object closing), which leaves no entry the sampler
could miss or catch differently. That is the named limit printed with every NOTHING_SEEN.
"""

import importlib.util
import subprocess
import sys
import time
from pathlib import Path

import pytest

psutil = pytest.importorskip("psutil")

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "push_watcher.py"
_spec = importlib.util.spec_from_file_location("push_watcher_real", _PATH)
pw = importlib.util.module_from_spec(_spec)
sys.modules["push_watcher_real"] = pw
_spec.loader.exec_module(pw)

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_SLEEP = "import time; time.sleep(60)  # " + pw.SIGNATURE


def _spawn(*argv):
    return subprocess.Popen(
        list(argv), creationflags=_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def _run_scenario(tmp_path, kill_one):
    raw = tmp_path / "raw.jsonl"
    hook = _spawn(sys.executable, "-c", "import time; time.sleep(60)")
    # The parent run: starts two workers, then idles. It outlives the scenario, as a real run outlives a dead worker.
    parent_code = (
        "import subprocess, sys, time\n"
        f"kids = [subprocess.Popen([sys.executable, '-c', {_SLEEP!r}]) for _ in range(2)]\n"
        "print(' '.join(str(k.pid) for k in kids), flush=True)\n"
        "time.sleep(60)\n"
    )
    parent = subprocess.Popen(
        [sys.executable, "-c", parent_code],
        stdout=subprocess.PIPE,
        creationflags=_NO_WINDOW,
        text=True,
    )
    pids = [int(x) for x in parent.stdout.readline().split()]
    watcher = _spawn(
        sys.executable, str(_PATH), "start", "--parent", str(hook.pid), "--raw", str(raw)
    )
    try:
        time.sleep(1.5)  # the watcher takes its baseline of who is present
        if kill_one:
            psutil.Process(pids[0]).kill()
        time.sleep(
            4.0
        )  # longer than the settle window, so the parent and sibling are seen still alive
        hook.kill()  # the push is over: the watcher must notice its parent is gone and stop on its own
        watcher.wait(timeout=20)
    finally:
        for proc in (hook, parent, watcher):
            if proc.poll() is None:
                proc.kill()
        for pid in pids:
            try:
                psutil.Process(pid).kill()
            except psutil.Error:
                pass
    return pids, pw.assemble(pw.read_raw(raw), 1, "odd failure")


def test_planted_fault_the_killed_helper_is_named(tmp_path):
    pids, report = _run_scenario(tmp_path, kill_one=True)
    assert report["outcome"] == pw.NAMED, report
    assert [d["pid"] for d in report["deaths"]] == [pids[0]]
    assert report["samples"] > 0


def test_planted_absence_nothing_is_named_when_nothing_died(tmp_path):
    _, report = _run_scenario(tmp_path, kill_one=False)
    assert report["outcome"] == pw.NOTHING_SEEN, report
    assert report["deaths"] == [] and report["samples"] > 0


def test_the_watcher_stops_by_itself_when_its_parent_is_gone(tmp_path):
    """Exits-when-parent-gone: a killed push cannot leave a stale watcher. _run_scenario would time out otherwise."""
    _run_scenario(tmp_path, kill_one=False)
