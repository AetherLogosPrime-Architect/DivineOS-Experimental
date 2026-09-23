"""The build-flow doorman holds when it should, whether or not its library loads.

The hook sourced the shared library with ``|| exit 0``, and exit 0 is ALLOW. The
library decides nothing -- it prints the footer after a refusal, and loading it
starts the hook's timing record -- so a library that would not load turned the
doorman into a permission, silently. walk-126cf863fe02.

HOW THE DECISION IS MADE REAL. The hook asks ``divineos work-item gate`` whether
to hold. A stand-in ``divineos`` placed first on PATH answers hold or pass. That
replaces the DEPENDENCY; the hook, which is what changed, runs for real. Every
case reaches the line it is about -- #544's push test did not, and passed
against the unfixed code, which is the failure this file is written against.

BOTH DIRECTIONS, and a third thing. A hold must survive a missing library; a
pass must stay a pass without it; and with the library present the hook must
still write its timing record, because hook_firing_map reads that record and
would call a working doorman SILENT without it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / ".claude" / "hooks" / "work-item-doorman.sh"
HOLD, PASS = 2, 0
PAYLOAD = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "src/x.py"}})


def _git_bash() -> str:
    """A bash PROVEN to run a script -- asked to exit 7, and it must say 7.

    Found beside git rather than by name: by name on Windows, the search order
    can reach the WSL stub, which runs nothing and fails every case the same
    way, so any comparison between two runs would pass against anything.
    """
    candidates = []
    git = shutil.which("git")
    if git:
        here = Path(git)
        candidates += [here.parents[1] / "bin" / "bash.exe", here.parents[2] / "bin" / "bash.exe"]
    found = shutil.which("bash")
    if found:
        candidates.append(Path(found))
    for c in candidates:
        if c.is_file():
            probe = subprocess.run([str(c), "-c", "exit 7"], capture_output=True, check=False)
            if probe.returncode == 7:
                return str(c)
    pytest.skip("no bash here can be shown to run a script")
    return ""


@pytest.fixture
def standin(tmp_path: Path):
    """A ``divineos`` that answers the gate with a chosen exit code."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "divineos"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "cat >/dev/null\n"
        'if [ "${STANDIN_RC:-0}" = "2" ]; then echo "HELD by the stand-in"; fi\n'
        'exit "${STANDIN_RC:-0}"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    return bin_dir


def _run(standin_dir: Path, tmp_path: Path, *, answer: int, library: bool):
    env = dict(os.environ)
    env["PATH"] = str(standin_dir) + os.pathsep + env.get("PATH", "")
    env["STANDIN_RC"] = str(answer)
    env["HOME"] = str(tmp_path / "home")
    cwd = REPO_ROOT if library else tmp_path  # outside a repo the library cannot be found
    return subprocess.run(
        [_git_bash(), str(HOOK)],
        input=PAYLOAD,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=env,
        check=False,
    )


def test_a_hold_is_a_hold_with_the_library(standin: Path, tmp_path: Path) -> None:
    """CONTROL: the stand-in says hold, and the hook passes that on."""
    out = _run(standin, tmp_path, answer=HOLD, library=True)
    assert out.returncode == HOLD, out.stderr[-400:]
    assert "HELD by the stand-in" in out.stderr


def test_a_hold_is_still_a_hold_without_the_library(standin: Path, tmp_path: Path) -> None:
    """THE FAULT. On main this exits 0: the load gave up and let the call through."""
    out = _run(standin, tmp_path, answer=HOLD, library=False)
    assert out.returncode == HOLD, (
        "the doorman let a held tool call through because a library it only "
        f"uses for its footer would not load:\n{out.stderr[-400:]}"
    )
    assert "HELD by the stand-in" in out.stderr


def test_a_pass_is_still_a_pass_without_the_library(standin: Path, tmp_path: Path) -> None:
    """THE OTHER DIRECTION. A door that refuses everything once its library
    vanishes would wedge the session, including the edit that repairs it."""
    assert _run(standin, tmp_path, answer=PASS, library=False).returncode == PASS


def test_a_pass_still_writes_the_timing_record(standin: Path, tmp_path: Path) -> None:
    """The reason the load stays at the top. hook_firing_map reads this log and
    would report a working doorman as SILENT if passes stopped writing it."""
    out = _run(standin, tmp_path, answer=PASS, library=True)
    assert out.returncode == PASS
    log = tmp_path / "home" / ".divineos" / "hook_timing.jsonl"
    assert log.is_file(), "no timing record was written on a pass"
    assert "work-item-doorman" in log.read_text(encoding="utf-8", errors="replace")
