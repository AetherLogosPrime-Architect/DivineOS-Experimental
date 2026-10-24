"""A note the read gate has delivered whole is context on an allowed command, never a refusal.

Dad, 2026-10-22, the 121st time this ask was filed from my own reflection notes (psf-de91f607):
"once the refusal prints the full text, the next command should pass instead of needing a second
try, and a doorbell re-arm should never be held by an unrelated note." The gate used to refuse the
command only to deliver the text, so every surfaced note cost one wasted call, and once it held the
doorbell restart over an unrelated note while Dad slept.

These drive the LIVE hook with a requirement pending, in the pair that makes the change mean
something: a note that fits is delivered with the command ALLOWED, and a note too long to inline
still HOLDS the command, because then a Read is genuinely owed. "It passes" alone would be satisfied
by a gate that holds nothing.
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


def _run(home: Path, command: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DIVINEOS_HOME": str(home)}
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        [BASH, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=REPO,
    )


def _pend(home: Path, note: Path) -> None:
    (home / "read_gate_pending.json").write_text(
        json.dumps(
            [
                {
                    "gate_id": "prior-writing",
                    "path": str(note),
                    "reason": "test: something handed and not opened",
                    "registered_at": time.time(),
                }
            ]
        ),
        encoding="utf-8",
    )


ACTION = "git commit -m x"


def test_a_note_that_fits_rides_along_and_the_command_passes(tmp_path):
    note = tmp_path / "short_note.md"
    note.write_text("# short\n\nthe whole note fits\n", encoding="utf-8")
    _pend(tmp_path, note)

    done = _run(tmp_path, ACTION)

    assert done.returncode == 0, (done.returncode, done.stderr[-400:])
    context = json.loads(done.stdout)["hookSpecificOutput"]
    assert context["hookEventName"] == "PreToolUse"
    assert "the whole note fits" in context["additionalContext"]
    assert "no need to open it again" in context["additionalContext"].lower()


def test_the_doorbell_restart_is_never_held_by_a_note_that_fits(tmp_path):
    note = tmp_path / "short_note.md"
    note.write_text("# short\n\nan unrelated note\n", encoding="utf-8")
    _pend(tmp_path, note)

    done = _run(tmp_path, "bash scripts/letter_doorbell.sh aether")

    assert done.returncode == 0, (done.returncode, done.stderr[-400:])


def test_a_note_too_long_to_inline_still_holds_the_action(tmp_path):
    note = tmp_path / "long_note.md"
    note.write_text("line\n" * 900, encoding="utf-8")
    _pend(tmp_path, note)

    done = _run(tmp_path, ACTION)

    assert done.returncode == 2, (done.returncode, done.stdout[-300:], done.stderr[-300:])
    assert "READ-GATE" in done.stderr


def test_the_delivered_note_is_not_owed_again_on_the_next_command(tmp_path):
    note = tmp_path / "short_note.md"
    note.write_text("# short\n\nonce is enough\n", encoding="utf-8")
    _pend(tmp_path, note)

    first = _run(tmp_path, ACTION)
    second = _run(tmp_path, ACTION)

    assert first.returncode == 0
    assert second.returncode == 0
    assert second.stdout.strip() == "", "delivered once, so nothing more is handed over"
