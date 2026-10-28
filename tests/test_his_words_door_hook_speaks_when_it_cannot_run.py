"""The words-door hook says so when it cannot run, instead of exiting in silence.

Aletheia's hold on #594, 2026-10-16: three early exits printed nothing, so a door that could not
run looked the same as a search that found nothing. The hook is copied into a bare folder with no
shared library beside it, which is the real shape of the second exit, and run for real.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "his-words-door-surface.sh"


def _bash() -> str:
    """Git Bash directly: a bare `bash` on Windows can resolve to WSL, which cannot run this."""
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        "/bin/bash",
        "bash",
    ):
        if Path(candidate).exists():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    pytest.skip("no usable bash interpreter for hook invocation")


def test_a_missing_shared_library_is_spoken_not_silent(tmp_path):
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(HOOK, hooks / HOOK.name)
    done = subprocess.run(
        [_bash(), str(hooks / HOOK.name)],
        input="{}",
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, "it must never block him"
    assert "## HE HAS SAID THIS BEFORE" in done.stdout
    assert "Could not run: the shared hook library is missing" in done.stdout
