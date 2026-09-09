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


def _surface_registered() -> bool:
    """Is the doorman live behind the PreToolUse doorbell, in the OS?

    THE DOORMAN MOVED, 2026-09-08. It now lives as a surface in
    ``core.hook_surfaces`` and its shell script's registration was retired in
    the same change, exactly as a migration should retire it. So the two tests
    below no longer ask about a line in the settings file — they ask whether
    the judgement is reachable at the door where it must refuse.

    This is the migration-aware version of the same guard. What Aletheia asked
    for was that the next split cannot happen silently; where the logic lives
    was never the point, and a test pinned to a location the logic has left is
    a test that fails on a correct change and passes on a broken one.
    """
    from divineos.core.hook_router import registered
    from divineos.core.hook_surfaces import install

    install()
    return "heredoc_escape" in registered("PreToolUse")


def test_the_doorman_is_registered_at_all() -> None:
    """The branch exists to connect it. Shipping it dark was the whole defect."""
    assert _surface_registered() or _registrations(), (
        "the heredoc doorman is reachable from neither the OS router nor a "
        "shell registration. A doorman that is never called cannot refuse "
        "anything."
    )


def test_the_doorman_runs_before_the_tool_it_guards() -> None:
    """PreToolUse, or it cannot refuse anything.

    A heredoc doorman consulted after the fact would report a fault the shell
    had already committed, which is the difference between a doorman and a
    post-mortem. In the OS the door IS the event, so registration at
    PreToolUse is the whole assertion; the Bash-only narrowing is the
    surface's own business and is covered where that logic lives.
    """
    if _surface_registered():
        return
    registrations = _registrations()
    assert registrations, "not registered at all; see the previous test"
    events = {event for event, _matcher in registrations}
    assert "PreToolUse" in events, f"registered only at {sorted(events)}"
    matchers = {matcher for event, matcher in registrations if event == "PreToolUse"}
    assert any(m and "Bash" in m for m in matchers), (
        f"PreToolUse matchers are {sorted(m for m in matchers if m)}; the doorman "
        "inspects Bash commands and must match Bash to see them"
    )


def test_the_guard_can_still_fail() -> None:
    """Control for the two above, because a check that cannot fail is the thing
    this file was written about. A name the router does not carry must not be
    reported as wired."""
    from divineos.core.hook_router import registered
    from divineos.core.hook_surfaces import install

    install()
    assert "heredoc_escape_that_does_not_exist" not in registered("PreToolUse")


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
