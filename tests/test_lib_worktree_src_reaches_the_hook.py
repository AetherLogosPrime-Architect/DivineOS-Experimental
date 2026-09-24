"""The worktree's src/ reaches every hook that sources _lib.sh.

2026-09-24 (Aether, build/dad-kept-and-known): the prepend lived only inside
find_divineos_python, and every hook calls it as PYTHON_BIN="$(find_divineos_python)".
Command substitution is a subshell, so the export died there and every hook in a
worktree silently ran the main checkout's code. Found when an end-to-end test of
the front-door hook could not import a module that existed only in the worktree.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / ".claude" / "hooks" / "_lib.sh"


def _bash():
    """Git Bash, never the WSL relay bare "bash" resolves to on this box."""
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        "/usr/bin/bash",
        shutil.which("bash") or "",
    ):
        if candidate and Path(candidate).exists() and "System32" not in candidate:
            return candidate
    return None


pytestmark = pytest.mark.skipif(
    _bash() is None, reason="no POSIX bash here -- could-not-look, which is not a pass"
)


def _run(script: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    done = subprocess.run(
        [_bash(), "-c", script],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def test_the_usual_call_leaves_this_trees_src_on_the_path():
    out = _run(
        'source .claude/hooks/_lib.sh; P="$(find_divineos_python)"; printf "%s" "$PYTHONPATH"'
    )
    assert out.replace("\\", "/").rstrip("/").endswith("/src"), out
    assert Path(out.split(";")[0].split(":")[-1] if ";" in out else out).parts[-1] == "src"


def test_sourcing_twice_does_not_stack_the_path():
    out = _run(
        "source .claude/hooks/_lib.sh; source .claude/hooks/_lib.sh; printf '%s' \"$PYTHONPATH\""
    )
    assert out.count("src") == 1, out
