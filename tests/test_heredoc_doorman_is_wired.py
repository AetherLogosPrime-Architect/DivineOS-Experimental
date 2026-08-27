"""The doorman is registered, and the registration is pinned by the suite.

WHY THIS EXISTS RATHER THAN LEANING ON THE EXISTING CHECKER.
``scripts/check_hook_wiring.py`` already does the general job -- every hook
registered, or saying out loud why it is not -- and it catches this exact case
by name, exiting non-zero with ``heredoc-escape-doorman.sh`` listed under DARK
HOOKS. It is wired into ``scripts/precommit.sh``.

It did not stop this, and the reason is not a defect in it. ``precommit.sh`` is
a preflight an operator runs by hand; the git pre-commit hook does not call it.
I committed a doorman whose entire purpose is the built-and-never-connected
class, without running the preflight that would have named it, so the branch
shipped the very thing it exists to fix.

This test is therefore not a second opinion. It moves ONE case out of a script
I have to remember to run and into the suite that runs on its own at push time.
Truth #11(a): where a mechanism leaves a choice-point, take the option away
rather than guarding it.

Aletheia asked for exactly this when she held the PR -- register it, and add a
test asserting the registration, "otherwise the next split does this again and
nothing says so."
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_SETTINGS = Path(__file__).resolve().parents[1] / ".claude" / "settings.json"
_DOORMAN = "heredoc-escape-doorman.sh"


def _registrations() -> list[tuple[str, str | None]]:
    data = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    return [
        (event, group.get("matcher"))
        for event, groups in data.get("hooks", {}).items()
        for group in groups
        for hook in group.get("hooks", [])
        if _DOORMAN in hook.get("command", "")
    ]


def test_the_doorman_is_registered_at_all() -> None:
    """The branch exists to connect it. Shipping it dark was the whole defect."""
    assert _registrations(), (
        f"{_DOORMAN} is written and registered nowhere. A hook that is never "
        "called cannot complain about not being called."
    )


def test_the_doorman_runs_before_the_tool_it_guards() -> None:
    """PreToolUse, on Bash, or it cannot refuse anything.

    A heredoc doorman registered after the fact would report a fault the shell
    had already committed, which is the difference between a doorman and a
    post-mortem.
    """
    registrations = _registrations()
    assert registrations, "not registered at all; see the previous test"
    events = {event for event, _matcher in registrations}
    assert "PreToolUse" in events, f"registered only at {sorted(events)}"
    matchers = {matcher for event, matcher in registrations if event == "PreToolUse"}
    assert any(m and "Bash" in m for m in matchers), (
        f"PreToolUse matchers are {sorted(m for m in matchers if m)}; the doorman "
        "inspects Bash commands and must match Bash to see them"
    )


def test_the_script_it_points_at_exists() -> None:
    """A registration naming a file that is not there is a louder kind of dark."""
    data = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    root = _SETTINGS.parents[1]
    for groups in data.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                command = hook.get("command", "")
                if _DOORMAN not in command:
                    continue
                target = root / command.split()[-1]
                assert target.is_file(), f"registration points at a missing file: {target}"


def test_settings_json_is_still_parseable() -> None:
    """Registration is a hand-edited file, and a broken one disarms every hook
    at once rather than only this one."""
    try:
        json.loads(_SETTINGS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - failure path
        pytest.fail(".claude/settings.json does not parse: " + str(exc))
