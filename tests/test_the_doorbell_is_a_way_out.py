"""The doorbell is the way out the Stop guard prescribes, so no guard holds it shut.

Aria, 2026-10-06. In one day three guards refused `bash scripts/letter_doorbell.sh
aria`: one knew a private list without it, one matched only the bare spelling and
refused the same command with a `cd` in front, and the read gate held it while the
voice hold refused the Read it asked for. The shared judge is `is_doorbell`.

These drive the LIVE read gate with a read pending, and the pair is the point: a
doorbell that passes proves nothing unless chained work and other scripts are held.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from divineos.core.remedy_allowlist import FORBIDDEN_HEADS, REMEDIES, is_doorbell

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "read-gate-doorman.sh"

PASSES = [
    "bash scripts/letter_doorbell.sh aria",
    "bash scripts/letter_doorbell.sh",
    f'cd "{REPO}" && bash scripts/letter_doorbell.sh aria',
    "set -o pipefail && bash scripts/letter_doorbell.sh aria",
]
HELD = [
    "bash scripts/letter_doorbell.sh aria; rm -rf scratch_nothing",
    "bash scripts/letter_doorbell.sh aria && git push",
    "bash scripts/other_script.sh aria",
    "echo bash scripts/letter_doorbell.sh aria",
    "rm -rf scratch_nothing",
    'bash scripts/letter_doorbell.sh "$(rm -rf x)"',
    "",
]


@pytest.mark.parametrize("command", PASSES)
def test_the_doorbell_is_recognised(command: str) -> None:
    assert is_doorbell(command)


@pytest.mark.parametrize("command", HELD)
def test_anything_else_is_not_the_doorbell(command: str) -> None:
    assert not is_doorbell(command)


def test_bash_stays_off_the_remedy_list() -> None:
    assert "bash" in FORBIDDEN_HEADS
    assert all(prefix[0] != "bash" for prefix in REMEDIES)


def _bash() -> str | None:
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        "/usr/bin/bash",
        shutil.which("bash") or "",
    ):
        if candidate and Path(candidate).exists() and "System32" not in candidate:
            return candidate
    return None


BASH = _bash()
live = pytest.mark.skipif(
    not HOOK.exists() or BASH is None,
    reason="hook or a POSIX bash absent here -- could-not-look, which is not a pass",
)


def _run(home: Path, command: str) -> int:
    env = {**os.environ, "DIVINEOS_HOME": str(home)}
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    proc = subprocess.run(
        [BASH, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=REPO,
    )
    return proc.returncode


@pytest.fixture
def pending_home(tmp_path: Path) -> Path:
    (tmp_path / "read_gate_pending.json").write_text(
        json.dumps(
            [
                {
                    "gate_id": "prior-writing",
                    "path": str(REPO / "README.md"),
                    "reason": "test: something handed and not opened",
                    "registered_at": time.time(),
                }
            ]
        ),
        encoding="utf-8",
    )
    return tmp_path


@live
@pytest.mark.parametrize("command", PASSES)
def test_the_read_gate_lets_the_doorbell_through(pending_home: Path, command: str) -> None:
    assert _run(pending_home, command) == 0


@live
@pytest.mark.parametrize("command", [c for c in HELD if c.strip()])
def test_the_read_gate_still_holds_everything_else(pending_home: Path, command: str) -> None:
    assert _run(pending_home, command) == 2
