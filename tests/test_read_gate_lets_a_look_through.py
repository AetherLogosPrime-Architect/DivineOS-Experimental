"""The read-gate doorman holds actions, never looks.

Aria, 2026-10-01. The doorman gated Bash wholesale, so with a match pending it
refused a bare grep -- the first action of two replies in a row, which Dad saw.
It now asks the house's one read-only judge about a shell line. These drive
the LIVE hook with a requirement pending: a look passes, an action is held.

The pair is the point. "A look passes" alone is satisfied by a doorman that
holds nothing; the held cases prove it is still a doorman.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "read-gate-doorman.sh"


# Bare "bash" here can resolve to the WSL relay, which exits 1 without running
# the hook -- the same trap test_advisory_hooks_stay_advisory names. It fooled
# the first replay of this change into reading "held" for a plain look.
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
pytestmark = pytest.mark.skipif(
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
    # A real, existing, non-scratch file, so the gate does not drop it as vanished.
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


@pytest.mark.parametrize(
    "command",
    [
        "grep -n x README.md",
        # Exactly as it was refused on 2026-10-01, second reply.
        'grep -rn "950\\|880\\|920\\|THRESHOLD" .claude/hooks/auto-cycle-token-trigger.sh | head; '
        'grep -rn "950_000\\|950000" src/divineos/core/auto_cycle.py | head',
    ],
)
def test_a_look_goes_through(pending_home: Path, command: str) -> None:
    assert _run(pending_home, command) == 0


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf scratch_nothing",
        "grep x README.md > out.txt",
        "ls x; rm -rf x",
        "sed -i s/a/b/ README.md",
        "lsblk",
        # Aletheia, reading #575 on 2026-10-01: a read verb that runs
        # something else. Main refused both; adding the read verbs opened them.
        "cat <(touch /tmp/pwn)",
        "rg --pre=/tmp/evil.sh x .",
        "rg --pre /tmp/evil.sh x .",
        "grep x <(rm y)",
    ],
)
def test_an_action_is_still_held(pending_home: Path, command: str) -> None:
    assert _run(pending_home, command) == 2


def test_a_flag_that_only_starts_with_pre_is_still_a_look() -> None:
    from divineos.hooks.pre_tool_use_gate import _is_readonly_probe

    assert _is_readonly_probe('grep -n "--pretty" README.md')
