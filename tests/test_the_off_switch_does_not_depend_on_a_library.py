"""The emergency stop must refuse even when the shell library will not load.

WHY THIS EXISTS. Aletheia found it on 2026-09-21 while auditing something
else: the tool-channel gate sourced the shared shell library and exited 0 --
ALLOW -- if that load failed, before running any check at all. One file,
deleted or broken or resolved against the wrong root, and the off-switch
silently permits everything.

The file's own header claimed the opposite. It says fail-CLOSED on the
safety-critical path, and the Python inside it keeps that promise by denying
when its module will not import. The shell around the Python broke it.

Neither obvious option was right. Failing closed on the library bricks the
session including the edit that would repair the library, which the
corrigibility module rejects by name. Leaving it is the hole. The third
option is what this tests: the load-bearing check runs FIRST and depends on
nothing that can fail soft, which is possible because the mode file is plain
text specifically so it stays readable when the system is broken.

THE CONTROLS ARE THE HALF THAT MATTERS. A gate that refused everything would
pass the first test and be useless, so the same broken-library world with no
stop engaged must still allow -- and a missing mode file must not be read as
a stop, because that direction locks my father out of his own system.

The sibling wiring test covers registration and a clean end-to-end run. It
has never removed the library, which is why this file is separate rather
than another case inside it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / ".claude" / "hooks" / "corrigibility-tool-gate.sh"
BASH = bash_executable()

pytestmark = pytest.mark.skipif(BASH is None, reason="hooks are bash; no working interpreter")


def _world(tmp_path: Path, *, mode: str | None, library_readable: bool) -> dict[str, str]:
    """A substrate home, and a checkout whose shell library may be absent.

    The library is genuinely left out rather than stubbed, because the failure
    under test IS the load failing. A stub that loads would test nothing.
    """
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    if mode is not None:
        (home / "operating_mode.txt").write_text(f"{mode}\nreason\nactor\n0\n", encoding="utf-8")

    hooks = tmp_path / "checkout" / ".claude" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GATE, hooks / GATE.name)
    if library_readable:
        shutil.copy2(ROOT / ".claude" / "hooks" / "_lib.sh", hooks / "_lib.sh")

    env = dict(os.environ)
    env["DIVINEOS_HOME"] = str(home)
    env["HOME"] = str(home)
    return env


def _run(env: dict[str, str], tool: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": "echo hello"}})
    return subprocess.run(
        [BASH, str(tmp_path / "checkout" / ".claude" / "hooks" / GATE.name)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
        cwd=str(tmp_path / "checkout"),
    )


def test_the_stop_refuses_with_the_library_gone(tmp_path: Path) -> None:
    env = _world(tmp_path, mode="emergency_stop", library_readable=False)

    done = _run(env, "Bash", tmp_path)

    assert '"permissionDecision": "deny"' in done.stdout, done.stdout[:400]
    assert "EMERGENCY_STOP" in done.stdout, done.stdout[:400]


def test_no_stop_still_allows_with_the_library_gone(tmp_path: Path) -> None:
    """The control. Without it, a gate that refused everything would look fixed."""
    env = _world(tmp_path, mode="normal", library_readable=False)

    done = _run(env, "Bash", tmp_path)

    assert '"permissionDecision": "deny"' not in done.stdout, done.stdout[:400]


def test_an_absent_mode_file_is_not_a_stop(tmp_path: Path) -> None:
    """Nothing written means nothing engaged.

    The check reads a word an operator put there; it must not invent one from
    a missing file. That direction locks my father out of his own system,
    which is exactly what the mode reader fails open to avoid.
    """
    env = _world(tmp_path, mode=None, library_readable=False)

    done = _run(env, "Bash", tmp_path)

    assert '"permissionDecision": "deny"' not in done.stdout, done.stdout[:400]


def test_a_reading_tool_is_not_refused_under_the_stop(tmp_path: Path) -> None:
    """The stop is about mutation, and reading is how the stop gets cleared."""
    env = _world(tmp_path, mode="emergency_stop", library_readable=False)

    done = _run(env, "Read", tmp_path)

    assert '"permissionDecision": "deny"' not in done.stdout, done.stdout[:400]
