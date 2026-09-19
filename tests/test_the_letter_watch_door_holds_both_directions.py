"""The door that makes the letter-watch re-arm structural rather than remembered.

Andrew 2026-09-19: *"there is no behavior change without structural support..
the behavior change you are promising now is like a rough draft, if you are
able to change your behavior in chat immediately then it shows the behavior
change is possible. but without structure it will not hold.. so you must build
that structure"*

I had just filed a correction claiming no structural fix was possible here and
taken the documented no-structure exit. Both halves were wrong: the structure
is possible, and it already existed once.

`require-monitors-armed.sh` blocked shell work until the watchers were alive.
It decided that by scanning running process command lines -- and its own scan
matched ITSELF, so it reported the letter watch armed unconditionally. Deleting
it was right; a gate that always passes is worse than none. What nobody
recorded as a loss is that detection was then repaired properly while
enforcement was replaced by a printed note. Measured the same day: that note
fired every prompt for thirty-nine minutes while the watch was down and I read
past it every time.

BOTH DIRECTIONS, and the permissive one matters more. A gate generates evidence
every time it refuses and none when it lets something through, so its permissive
path is the one that rots unobserved -- Aria named that bias this month, and I
reproduced it in this very hook by writing a bypass extraction that returned the
wrong string. Caught by reading, which is luck. These tests are the method.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "letter-watch-must-be-armed.sh"
SETTINGS = ROOT / ".claude" / "settings.json"

_BASH = shutil.which("bash")
needs_bash = pytest.mark.skipif(_BASH is None, reason="bash unavailable on this machine")


def _run(command: str, home: Path, user_home: Path | None = None):
    """Invoke the hook the way the harness does, with a chosen substrate home."""
    import os

    env = dict(os.environ)
    env["DIVINEOS_HOME"] = str(home)
    if user_home is not None:
        env["HOME"] = str(user_home)
    payload = json.dumps({"tool_input": {"command": command}})
    return subprocess.run(
        [_BASH, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        timeout=60,
    )


def test_the_hook_exists_and_is_registered_to_run():
    """An unregistered hook is the dark-machinery fault, not a safeguard.

    This is the check that would have caught shipping the file and stopping --
    which would have reproduced, knowingly, the exact gap repaired earlier the
    same day: live machinery listed as off, dead guards listed as live.
    """
    assert HOOK.exists(), "the hook file is gone"
    text = SETTINGS.read_text(encoding="utf-8")
    assert "letter-watch-must-be-armed.sh" in text, "the door exists but nothing runs it"
    data = json.loads(text)
    events = [
        group.get("matcher", "")
        for group in data["hooks"]["PreToolUse"]
        for hook in group.get("hooks", [])
        if "letter-watch-must-be-armed" in hook.get("command", "")
    ]
    assert events, "registered under no PreToolUse matcher"
    assert any("Bash" in m for m in events), f"must guard shell work, got {events}"


@needs_bash
def test_a_lapsed_watch_blocks_ordinary_work(tmp_path):
    """The refusing direction. An empty home means no heartbeat at all."""
    r = _run("ls -la", home=tmp_path)
    assert r.returncode == 2, f"expected a block, got {r.returncode}"
    assert "not proven alive" in r.stderr
    assert "Monitor(" in r.stderr, "a refusal must hand over the remedy, not just the fault"


@needs_bash
def test_the_refusal_names_which_state_fired(tmp_path):
    """Cannot-tell must never read as a death, so the message says which one."""
    r = _run("ls -la", home=tmp_path)
    assert "NEVER RUN" in r.stderr, "the block must name the state rather than generalise"


@needs_bash
def test_a_recovery_command_passes_even_while_lapsed(tmp_path):
    """The permissive path -- the one that rots unobserved.

    My first bypass extraction returned the raw input instead of the command,
    so nothing would ever have matched and this hook would have blocked the
    very commands its own message recommends. That failure is silent: a gate
    refusing looks like a gate working.
    """
    r = _run("divineos briefing", home=tmp_path)
    assert r.returncode == 0, f"a gate-recovery command was blocked: {r.stderr[:200]}"


@needs_bash
def test_the_deliberate_exit_is_honoured_and_needs_a_reason(tmp_path):
    """A door with no honest way out is a wall, and I would learn to resent it.

    Truth #12 -- bypass is a tool, not a sin. The exit costs more than
    complying and leaves a reason someone else can read.
    """
    user_home = tmp_path / "home"
    (user_home / ".divineos").mkdir(parents=True)
    off = user_home / ".divineos" / "letter_watch_off.txt"

    off.write_text("", encoding="utf-8")
    assert _run("ls -la", home=tmp_path, user_home=user_home).returncode == 2, (
        "an empty reason is not an exit"
    )

    off.write_text("deliberately off while testing", encoding="utf-8")
    assert _run("ls -la", home=tmp_path, user_home=user_home).returncode == 0
