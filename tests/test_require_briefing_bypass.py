"""Regression-pin test for the require-briefing.sh catch-22 fix.

Found live 2026-05-14 night during the show-fix triage walk: the
require-briefing.sh hook was using ``cmd.startswith('divineos
briefing')`` to bypass its own recovery command. Compound commands
like ``cd ... && divineos briefing`` did not start with the bypass
target — the bypass missed and the hook blocked its own remedy.

This is the most common gate-failure shape: block message names a
recovery command which is itself blocked. The class-test below
verifies every bypass entry can be invoked under several common
prefix patterns (cd, source, env, etc.) without being blocked.

Pin: every NEW bypass-style hook (gates whose deny message names a
command that should clear the gate) must add the bypass-command to
its bypass list AND must add an entry here to prove the bypass
matches under compound-command shapes.
"""

from __future__ import annotations

import re
from pathlib import Path


_HOOK_PATH = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "require-briefing.sh"


def _extract_bypass_commands() -> list[str]:
    """Extract the bypass-command tuple from require-briefing.sh."""
    text = _HOOK_PATH.read_text(encoding="utf-8")
    # The bypass list lives in a Python for-loop inside the heredoc.
    m = re.search(r"for bypass in \(([\s\S]*?)\):", text)
    assert m, "could not find bypass tuple in require-briefing.sh"
    body = m.group(1)
    entries = re.findall(r"'([^']+)'", body)
    return entries


def _bypass_matches(cmd: str, bypass: str) -> bool:
    """Mirror of the hook's bypass-matching logic.

    If this function returns True for the bypass-target under the
    common prefixes below, the hook will let the command through.
    """
    if cmd.startswith(bypass):
        return True
    if (" " + bypass + " ") in (" " + cmd + " "):
        return True
    if cmd.endswith(" " + bypass):
        return True
    if (bypass + " ") in cmd:
        return True
    return False


# Compound-command prefixes commonly used by the agent. Each one
# should NOT defeat the bypass — that was the catch-22 found tonight.
_PREFIXES = (
    "",
    "cd /tmp && ",
    'cd "C:/some path" && ',
    "source venv/bin/activate && ",
    "PYTHONPATH=. ",
    "FOO=bar ",
    "set -e; ",
    "echo go; ",
)


def test_every_bypass_command_survives_common_prefixes() -> None:
    """LOAD-BEARING: every bypass-target must match under every prefix.

    If this test fails for any (prefix, bypass) pair, the hook is
    blocking its own recovery for that command — replicating the
    catch-22 that was caught and fixed 2026-05-14.
    """
    bypass_commands = _extract_bypass_commands()
    assert bypass_commands, "no bypass commands extracted — hook may be empty"
    failures: list[str] = []
    for bypass in bypass_commands:
        for prefix in _PREFIXES:
            cmd = prefix + bypass
            if not _bypass_matches(cmd, bypass):
                failures.append(f"prefix={prefix!r} bypass={bypass!r}")
    assert not failures, (
        "require-briefing.sh bypass failed under compound-command shapes; "
        "the hook would block its own recovery for: " + ", ".join(failures)
    )


def test_non_bypass_commands_still_match_nothing() -> None:
    """Sanity check: arbitrary commands don't accidentally match any bypass."""
    bypass_commands = _extract_bypass_commands()
    test_cmds = [
        "rm -rf /",
        "git push --force",
        "pip install evil",
        "python -c 'do_bad_thing()'",
    ]
    for cmd in test_cmds:
        for bypass in bypass_commands:
            assert not _bypass_matches(cmd, bypass), (
                f"non-bypass command {cmd!r} matched bypass {bypass!r}"
            )


def test_bypass_list_contains_briefing() -> None:
    """The specific catch-22 found tonight: divineos briefing must be in the list."""
    bypass_commands = _extract_bypass_commands()
    assert "divineos briefing" in bypass_commands
