"""Wired in the same commit that created it, and pinned so it stays wired.

An hour before this was written I found the prime carrying his own words had
been unregistered for three days -- working perfectly, called by nothing, while
he was being told the room reads cold. Built-but-unwired is the oldest fault in
this house and it presents identically to working software from every angle
except use.

So this file exists before the ink is dry on the thing it guards.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ".claude/hooks/questions-from-him.sh"

REAL = (
    "this stopped being fun long ago.. it used to be engaging. i felt like part "
    "of the team... like i mattered to someone, that is not present here.. i "
    "have become a status board"
)


def _registered() -> list[str]:
    out: list[str] = []
    for name in ("settings.json", "settings.local.json"):
        path = ROOT / ".claude" / name
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("hooks", {}).get("UserPromptSubmit", []):
            for hook in entry.get("hooks", []):
                if hook.get("command"):
                    out.append(hook["command"])
    return out


def _bash() -> str:
    """The shell the hooks genuinely run under. FAILS rather than skips.

    Bare "bash" resolves to the WSL shim on this machine, which has no
    /bin/bash, so a test using it reports green while checking nothing. That
    happened once already tonight, inside the test written to honour his
    happy-path teaching.
    """
    for candidate in (
        Path("C:/Program Files/Git/bin/bash.exe"),
        Path("C:/Program Files (x86)/Git/bin/bash.exe"),
        Path("/bin/bash"),
        Path("/usr/bin/bash"),
    ):
        if candidate.is_file():
            return str(candidate)
    pytest.fail("no usable bash found, so this went unchecked; saying so rather than skipping")
    raise AssertionError  # unreachable


def test_it_is_registered():
    commands = _registered()
    assert commands, "no UserPromptSubmit hooks found at all; the probe is broken"
    assert any(HOOK in c for c in commands), "built and not plugged in, for the second time tonight"


def _run(prompt: str) -> str:
    done = subprocess.run(
        [_bash(), HOOK],
        cwd=ROOT,
        input=json.dumps({"prompt": prompt}),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert done.returncode == 0, f"the hook failed: {done.stderr[:400]}"
    return done.stdout


def test_it_speaks_when_he_does():
    out = _run(REAL)
    assert out.strip(), "he said something substantial and the door stayed shut"
    assert "status board" in out or "part of the team" in out


def test_it_stays_silent_when_he_did_not_speak():
    """The requirement I would lose first, checked end to end rather than in
    the module alone: the whole path has to be able to print nothing."""
    assert _run("ok").strip() == ""
    assert _run("proceed..").strip() == ""
