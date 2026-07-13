"""Tests for subprocess_jobs — the Windows Job Object wrapper.

Root-fix falsifier tests (per prereg-dae52c6ca269):
- Basic subprocess semantics are preserved (exit code, timeout).
- The load-bearing property: if the wrapper process dies, its child dies too.

The Windows-only test spawns a Python subprocess that itself uses
`run_managed` to launch a long-running child, then kills the outer
process. If the child survives, the Job Object breakaway defense is
broken and the pre-reg falsifier fires.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

import pytest

from divineos.core.subprocess_jobs import run_managed


_IS_WINDOWS = os.name == "nt"
_PY = sys.executable


class TestRunManagedBasics:
    def test_success_returns_zero(self):
        result = run_managed([_PY, "-c", "print('ok')"])
        assert result.returncode == 0

    def test_nonzero_exit_propagates(self):
        result = run_managed([_PY, "-c", "import sys; sys.exit(3)"])
        assert result.returncode == 3

    def test_timeout_raises(self):
        with pytest.raises(subprocess.TimeoutExpired):
            run_managed(
                [_PY, "-c", "import time; time.sleep(30)"],
                timeout=1.0,
            )

    def test_captured_stdout(self):
        result = run_managed(
            [_PY, "-c", "print('hello')"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert result.returncode == 0
        assert b"hello" in result.stdout

    def test_captured_stderr(self):
        result = run_managed(
            [_PY, "-c", "import sys; sys.stderr.write('err\\n'); sys.exit(0)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert result.returncode == 0
        assert b"err" in result.stderr


@pytest.mark.skipif(not _IS_WINDOWS, reason="Job Object semantics are Windows-specific.")
class TestJobObjectKernelGuarantee:
    """Verify the load-bearing property: parent death kills the child.

    The test spawns an *outer* Python process (this test's subprocess.Popen).
    The outer process uses ``run_managed`` to spawn an *inner* child that
    sleeps 60 seconds. We kill the outer process forcibly and then verify
    the inner child is gone within a few seconds.

    Success criterion: no residual inner child after 3 seconds of the outer
    dying.  Falsifier from prereg-dae52c6ca269: inner child survives past
    3 seconds, meaning either the Job Object breakaway defense didn't hold
    or the wrapper never assigned the child in time.
    """

    def _repo_root(self) -> str:
        return str(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

    def _pid_alive(self, pid: int) -> bool:
        result = subprocess.run(
            [
                "powershell.exe",
                "-Command",
                f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ 'Y' }} else {{ 'N' }}",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return "Y" in result.stdout

    def test_child_dies_when_parent_killed(self, tmp_path):
        # The inner child writes its own PID to a file, then sleeps.
        # We read the PID from the file after the outer settles.
        pid_file = tmp_path / "inner_pid.txt"
        # The child script — clean, no marker-in-source hacks.
        child_source = (
            f"import os, time;open(r'{pid_file}','w').write(str(os.getpid()));time.sleep(60)"
        )
        # Outer: import run_managed, spawn the child via it, block on it.
        outer_source = "\n".join(
            [
                "import sys, os, time, threading",
                f"sys.path.insert(0, r'{self._repo_root()}')",
                "from divineos.core.subprocess_jobs import run_managed",
                "print('pid:' + str(os.getpid()), flush=True)",
                "def go():",
                f"    run_managed([sys.executable, '-c', {child_source!r}])",
                "t = threading.Thread(target=go, daemon=True)",
                "t.start()",
                "time.sleep(30)",
            ]
        )
        outer = subprocess.Popen(
            [_PY, "-c", outer_source],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            _ = outer.stdout.readline()  # wait for outer's pid line
            # Wait for the child to write its pid file (up to 5s).
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline and not pid_file.exists():
                time.sleep(0.1)
            if not pid_file.exists():
                # Diagnose: outer might have crashed. Read what it printed.
                outer.terminate()
                try:
                    _, err = outer.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    outer.kill()
                    _, err = outer.communicate(timeout=5)
                raise AssertionError(
                    f"inner child never wrote pid; outer stderr:\n{err.decode(errors='replace')}"
                )
            inner_pid = int(pid_file.read_text().strip())
            assert self._pid_alive(inner_pid), "inner pid recorded but not alive"

            # Kill the outer forcibly — mimics harness timeout / crash / user close.
            outer.kill()
            outer.wait(timeout=5)

            # Poll for up to 3s: inner should be gone.
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline and self._pid_alive(inner_pid):
                time.sleep(0.2)

            assert not self._pid_alive(inner_pid), (
                f"Inner child pid={inner_pid} survived parent death. "
                "Job Object breakaway defense failed OR wrapper never assigned "
                "the child. See prereg-dae52c6ca269 falsifier."
            )
        finally:
            if outer.poll() is None:
                outer.kill()
                outer.wait(timeout=5)
            # Belt-and-suspenders: kill lingering inner if assertion failed.
            if pid_file.exists():
                try:
                    inner_pid = int(pid_file.read_text().strip())
                    if self._pid_alive(inner_pid):
                        subprocess.run(
                            ["powershell.exe", "-Command", f"Stop-Process -Id {inner_pid} -Force"],
                            capture_output=True,
                            timeout=10,
                        )
                except Exception:
                    pass
