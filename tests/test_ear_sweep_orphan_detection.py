"""Orphan detection in the ear_watch sweeper (2026-08-01).

The sweeper had never reaped anything. It scanned ``tasklist /V /FO CSV``
for the string ``ear_watch.py``, and tasklist does not emit command-line
arguments at any verbosity — so the substring could never match and the
finder returned ``[]`` on every call since it was written.

Measured 2026-08-01: rows in that tasklist output containing
``ear_watch.py`` = 0, live watchers per CIM = 4.

The silence cost more than the leak. A 2026-06-13 sleep-hang
investigation recorded "verified 0 stale processes at session start via
the sweep hook" and ruled the leak out as a cause on that basis
(knowledge e0c0c879). The empty return was read as evidence of health.

These tests are weighted toward what must NOT be killed, because the only
thing the caller does with a match is kill it. Three real defects were
found by measuring against the live process table during the rewrite, not
by re-reading the code, and each has a test here:

  1. matching the string anywhere in the command line also matched bash
     shells, nohup wrappers, and the inspecting process itself
  2. checking only the immediate parent missed the real shape, which is
     (dead launcher) -> nohup -> python, where nohup is still alive
  3. a bare prefix test claimed Aria's ``...-Experimental-Aria-new``
     worktree as this repo's, because it startswith ``...-Experimental``
"""

from __future__ import annotations

from divineos.core.ear_sweep import _ancestry_is_broken, _is_ear_watch_process

ROOT = "c:/divine os/divineos-experimental"
SIBLING = "c:/divine os/divineos-experimental-aria-new"


# --- what counts as a watcher -------------------------------------------


def test_python_running_the_script_matches():
    cmd = ["python.exe", f"{ROOT}/family/ear_watch.py", "--member", "aether"]
    assert _is_ear_watch_process("python.exe", cmd, ROOT) is True


def test_windows_backslash_paths_match():
    cmd = ["python.exe", "c:\\DIVINE OS\\DivineOS-Experimental\\family\\ear_watch.py"]
    assert _is_ear_watch_process("python.exe", cmd, ROOT) is True


# --- what must NOT be killed --------------------------------------------


def test_bash_shell_mentioning_the_script_is_not_a_watcher():
    cmd = ["bash.exe", "-c", "source snap; nohup python family/ear_watch.py"]
    assert _is_ear_watch_process("bash.exe", cmd, ROOT) is False


def test_nohup_wrapper_is_not_a_watcher():
    cmd = ["nohup.exe", f"{ROOT}/.venv/Scripts/python.exe", "family/ear_watch.py"]
    assert _is_ear_watch_process("nohup.exe", cmd, ROOT) is False


def test_inline_source_mentioning_the_script_is_not_a_watcher():
    """The scan must not kill the process doing the scanning. A ``-c``
    payload that merely contains the name is not running the script."""
    cmd = ["python.exe", "-c", "from x import y\nprint('ear_watch.py check')"]
    assert _is_ear_watch_process("python.exe", cmd, ROOT) is False


def test_sibling_worktree_is_not_this_checkout():
    """Aria's worktree path startswith this repo's path. A bare prefix
    test claims her live watchers as ours and reaps them mid-session."""
    cmd = ["python.exe", f"{SIBLING}/family/ear_watch.py", "--member", "aria"]
    assert _is_ear_watch_process("python.exe", cmd, ROOT) is False
    # ...and is correctly hers when her own session sweeps.
    assert _is_ear_watch_process("python.exe", cmd, SIBLING) is True


def test_no_repo_scope_matches_any_checkout():
    cmd = ["python.exe", f"{SIBLING}/family/ear_watch.py"]
    assert _is_ear_watch_process("python.exe", cmd, None) is True


# --- ancestry ------------------------------------------------------------


def _fake_tree(monkeypatch, tree: dict[int, tuple[str, int]]):
    """Install a fake process tree: pid -> (name, ppid)."""
    import psutil

    class FakeProc:
        def __init__(self, pid):
            if pid not in tree:
                raise psutil.NoSuchProcess(pid)
            self._pid = pid

        def name(self):
            return tree[self._pid][0]

        def ppid(self):
            return tree[self._pid][1]

    monkeypatch.setattr(psutil, "Process", FakeProc)


def test_live_session_above_means_owned(monkeypatch):
    """bash -> claude. A live session is above it, so it is owned."""
    _fake_tree(monkeypatch, {200: ("bash.exe", 300), 300: ("claude.exe", 400)})
    assert _ancestry_is_broken(200, {200, 300}) is False


def test_chain_ending_in_dead_ancestor_is_NOT_automatically_orphan(monkeypatch):
    """Guards the exact bug measuring caught. On Windows every chain ends
    in a dead ancestor — a launcher exiting and leaving explorer.exe
    parentless is normal. The first implementation called that an orphan
    and so classified every process on the machine, including the live
    one running the check. If this test ever fails, that bug is back."""
    _fake_tree(
        monkeypatch,
        {
            200: ("bash.exe", 300),
            300: ("claude.exe", 400),
            400: ("explorer.exe", 999),  # 999 is dead
        },
    )
    assert _ancestry_is_broken(200, {200, 300, 400}) is False


def test_no_session_above_is_orphan(monkeypatch):
    """The real leak shape: python -> nohup -> dead launcher, no session
    anywhere above. nohup is alive, so an immediate-parent check calls it
    healthy while nothing will ever shut it down."""
    _fake_tree(monkeypatch, {200: ("nohup.exe", 999)})
    assert _ancestry_is_broken(200, {200, 300}) is True


def test_parent_zero_or_missing_is_orphan():
    assert _ancestry_is_broken(0, {100}) is True
    assert _ancestry_is_broken(None, {100}) is True


def test_cycle_does_not_hang(monkeypatch):
    """PID reuse can in principle produce a loop. A reaper that hangs at
    SessionStart is worse than one that misses an orphan."""
    _fake_tree(monkeypatch, {10: ("a.exe", 20), 20: ("b.exe", 10)})
    assert _ancestry_is_broken(10, {10, 20}) is True


def test_unknowable_ancestry_does_not_kill(monkeypatch):
    """Lookup failure means we cannot establish ownership. Refuse to kill
    on a guess — a missed orphan is cheap, a wrongly-killed live watcher
    breaks the letter channel mid-conversation."""
    _fake_tree(monkeypatch, {})
    assert _ancestry_is_broken(500, {500}) is False
