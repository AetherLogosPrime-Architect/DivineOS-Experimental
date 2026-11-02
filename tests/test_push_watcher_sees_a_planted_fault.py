"""The real sampler, against a real killed worker, against its absence, and against someone else's worker.

Turing's finding (walk-193e1c70464f): a watcher that works and one that merely runs return the same value on a quiet
push, so the only proof is to plant the fault AND its absence. The first test kills a helper on purpose while its
parent and its sibling keep running and asserts the report names it. The second runs the identical setup with no kill
and asserts the report names nothing. The third kills a helper that belongs to ANOTHER push running at the same time
and asserts the report still names nothing: found when three copies of this file ran at once and each watcher blamed
the others' deaths on its own push, which is exactly Dad and Aether pushing together.

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

# A test run: starts two workers, prints their pids, then idles. It outlives a dead worker, as a real run does.
_PARENT_RUN = (
    "import subprocess, sys, time\n"
    f"kids = [subprocess.Popen([sys.executable, '-c', {_SLEEP!r}]) for _ in range(2)]\n"
    "print(' '.join(str(k.pid) for k in kids), flush=True)\n"
    "time.sleep(60)\n"
)
# The push hook stand-in: starts a test run as its child, passes the worker pids on, then idles.
_HOOK = (
    "import subprocess, sys, time\n"
    f"run = subprocess.Popen([sys.executable, '-c', {_PARENT_RUN!r}], stdout=subprocess.PIPE, text=True)\n"
    "print(run.stdout.readline().strip(), flush=True)\n"
    "time.sleep(60)\n"
)


def _spawn(*argv):
    return subprocess.Popen(
        list(argv), creationflags=_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def _start_run(code):
    proc = subprocess.Popen(
        [sys.executable, "-c", code], stdout=subprocess.PIPE, creationflags=_NO_WINDOW, text=True
    )
    return proc, [int(x) for x in proc.stdout.readline().split()]


def _wait_until_seen(raw, pids, timeout=30.0):
    """Block until the watcher's log shows every stand-in worker as present: the plant waits for the instrument.

    This test once failed one run in five because it killed the helper after a fixed 1.5 s, before a loaded machine
    let the watcher finish its first look. A kill before the baseline is not a missed death, it is an unplanted fault.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        seen = {
            int(e["pid"]) for e in pw.read_raw(raw) if e.get("k") == "present" and e.get("worker")
        }
        if set(pids) <= seen:
            return
        time.sleep(0.2)
    raise AssertionError(
        f"the watcher never recorded the workers {pids} as present within {timeout}s"
    )


def _run_scenario(tmp_path, kill_own=False, kill_decoy=False):
    raw = tmp_path / "raw.jsonl"
    hook, own = _start_run(_HOOK)  # the watched push: hook -> test run -> two workers
    decoy, others = _start_run(_PARENT_RUN)  # ANOTHER push's run, not under the hook
    watcher = _spawn(
        sys.executable, str(_PATH), "start", "--parent", str(hook.pid), "--raw", str(raw)
    )
    try:
        _wait_until_seen(raw, own)
        if kill_own:
            psutil.Process(own[0]).kill()
        if kill_decoy:
            psutil.Process(others[0]).kill()
        time.sleep(
            4.0
        )  # longer than the settle window, so the parent and sibling are seen still alive
        hook.kill()  # the push is over: the watcher must notice its parent is gone and stop on its own
        watcher.wait(timeout=20)
    finally:
        for proc in (hook, decoy, watcher):
            if proc.poll() is None:
                proc.kill()
        for pid in own + others:
            try:
                psutil.Process(pid).kill()
            except psutil.Error:
                pass
    return own, pw.assemble(pw.read_raw(raw), 1, "odd failure")


def test_planted_fault_the_killed_helper_is_named(tmp_path):
    own, report = _run_scenario(tmp_path, kill_own=True)
    assert report["outcome"] == pw.NAMED, report
    assert [d["pid"] for d in report["deaths"]] == [own[0]]
    assert report["samples"] > 0


def test_planted_absence_nothing_is_named_when_nothing_died(tmp_path):
    _, report = _run_scenario(tmp_path)
    assert report["outcome"] == pw.NOTHING_SEEN, report
    assert report["deaths"] == [] and report["samples"] > 0


def test_another_pushes_dead_helper_is_not_this_pushes_death(tmp_path):
    """Concurrent pushes: a worker that is not under the watched hook ending is none of this watcher's business."""
    _, report = _run_scenario(tmp_path, kill_decoy=True)
    assert report["deaths"] == [], report
    assert report["outcome"] == pw.NOTHING_SEEN, report


def test_a_process_number_handed_to_someone_else_is_not_my_hook():
    """Aletheia, 2026-10-23: 'is my parent alive?' must mean THAT parent. The start time pins it."""
    me = psutil.Process()
    assert pw._alive(me.pid), "control: the running test process is alive"
    assert pw._alive(me.pid, created=me.create_time()), (
        "control: the same process, correctly pinned, is alive"
    )
    assert not pw._alive(me.pid, created=0.0), (
        "a number held by a process that started at another time is not it"
    )
    assert not pw._alive(2**22 + 12345), "a number nobody holds is gone"


@pytest.mark.skipif(
    sys.platform == "win32", reason="a program run under another name needs a Unix symlink"
)
@pytest.mark.parametrize("alias", ["python3", "python3.12", "python"])
def test_a_worker_is_seen_whatever_the_interpreter_is_called(tmp_path, alias):
    """Aletheia, 2026-10-23: the watcher listed Python as python / python.exe only, so on a machine where it runs as
    python3 it never saw a worker and said 'nothing seen' while blind. A real child, started through a link NAMED
    `alias`, must be recognised. The premise (what name the system reports) is asserted, and 'python' is the control that
    the old list also passed."""
    link = tmp_path / alias
    # link-target-outside-tmp: the link points at the interpreter FILE, never a folder, so cleanup can only remove the link; it is also removed below
    link.symlink_to(sys.executable)
    child = subprocess.Popen(
        [str(link), "-c", _SLEEP], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        time.sleep(1.0)
        assert psutil.Process(child.pid).name() == alias, (
            "the premise: the system reports the link's name"
        )
        seen = pw._snapshot({}, None)
        assert child.pid in seen and seen[child.pid]["worker"], (
            f"a worker under the name {alias!r} was not recognised"
        )
    finally:
        child.kill()
        child.wait()
        link.unlink()  # remove the link itself, which is all this does: it never touches the file it points at


@pytest.mark.skipif(
    sys.platform == "win32", reason="a zombie (killed, not yet collected) only exists on Unix"
)
def test_a_killed_process_nobody_has_collected_counts_as_gone():
    """The Linux leak: pid_exists calls a zombie alive, so the watcher never noticed its hook was gone and ran on for ever.

    The control is the same call on the same child while it is alive, which must say alive."""
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        time.sleep(0.5)
        assert pw._alive(child.pid), "control: a live child is alive"
        child.kill()
        time.sleep(0.5)  # killed, and nobody has called wait(): it is now a zombie
        assert psutil.pid_exists(child.pid), "the premise: pid_exists still says yes for it"
        assert not pw._alive(child.pid), "a zombie is a hook that has exited"
    finally:
        child.wait()


def test_the_watcher_stops_by_itself_when_its_parent_is_gone(tmp_path):
    """Exits-when-parent-gone: a killed push cannot leave a stale watcher. _run_scenario would time out otherwise."""
    _run_scenario(tmp_path)
