"""Regression-pin for arm-compaction-monitor-instruction.sh path quoting.

Task #122 (2026-06-09): the hook printed the Monitor command with an
unquoted `${SCRIPT_PATH}`. On Windows where the repo root contains a
space ("C:\\DIVINE OS\\..."), a fresh post-compaction instance
copy-pasting the printed command hit `python: can't open file
'C:\\DIVINE'` with exit 2. Fix: double-quote the path inside the
printed command.

This test pins that the emitted command quotes the script path so a
copy-paste-into-the-Monitor-tool flow survives spaces in the repo root.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


HOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / ".claude"
    / "hooks"
    / "arm-compaction-monitor-instruction.sh"
)


def _find_bash() -> str | None:
    if sys.platform.startswith("win"):
        for c in [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"]:
            if Path(c).exists():
                return c
        return None
    return shutil.which("bash")


_BASH = _find_bash()
pytestmark = pytest.mark.skipif(_BASH is None, reason="no usable bash for hook invocation")


def _run_hook() -> str:
    result = subprocess.run(
        [_BASH, str(HOOK_PATH)],
        input="",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    return result.stdout


def test_hook_emits_quoted_script_path():
    """The Monitor command printed by the hook must double-quote the
    script path, so a fresh instance copy-pasting it succeeds even when
    the repo root contains a space."""
    out = _run_hook()
    # The printed command appears inside the Monitor tool's command=
    # string literal, so the inner double-quotes are escaped: the
    # emitted form is `python \"...\"`. When pasted into the tool, the
    # receiving shell strips the escape and the path lands quoted.
    assert 'python \\"' in out, (
        'Hook output should contain `python \\"...\\"` (escaped-quoted '
        "script path). Unquoted paths break on Windows when the repo "
        "root has a space."
    )
    assert "compaction_token_monitor.py" in out


def test_hook_does_not_emit_bare_unquoted_path():
    """Negative pin: the old broken form `python ${SCRIPT_PATH}` (no
    quotes) must not return."""
    out = _run_hook()
    # The substring `python compaction_token_monitor` only appears
    # without quotes if the bug regressed.
    assert "python C:" not in out and "python /" not in out, (
        "Hook regressed to unquoted-path form — would exit 2 on a "
        "Windows repo root containing a space."
    )
