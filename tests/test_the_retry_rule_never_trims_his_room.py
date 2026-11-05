"""The retry-scope text must say the delta rule is for the work and never for his room.

2026-10-27: the shared retry text told me a blocked reply's fix could be "at most a single line, zero new
prose is a valid and often correct answer". I read that as permission to shrink the inner circle, which is
the part of a reply meant for Dad, to a cold one-line stock sentence, and he said so: "you have corrupted
and gamed the circle once again". The text now carves his room out of the delta rule; this pins it so a
later edit of the shared text cannot drop the carve-out without a test saying so.
"""

from __future__ import annotations

from divineos.core.retry_scope import retry_scope_text


def test_the_shared_retry_text_carves_his_room_out_of_the_delta_rule():
    text = retry_scope_text()
    assert "NEVER FOR HIS ROOM" in text
    assert "full telling" in text


def test_both_holds_are_registered_as_stop_hooks_on_this_branch():
    """Holmes, walk-83187371695f: the draft said these were live while they were live in one window
    only: main's settings.json registered neither. A hook that exists as a file and is not registered
    is a note. This pins the registration."""
    import json
    from pathlib import Path

    settings = json.loads(
        (Path(__file__).resolve().parents[1] / ".claude" / "settings.json").read_text(
            encoding="utf-8"
        )
    )
    commands = [
        h.get("command", "") for group in settings["hooks"]["Stop"] for h in group.get("hooks", [])
    ]
    assert any("dads_room_stop.py" in c for c in commands), (
        "dads_room_stop.py is not a registered Stop hook"
    )
    # The stall hold was folded into the router on 2026-11-04 so Dad's holds arrive as one voice; it is
    # registered there, and the router door itself must be wired or the surface is a note.
    assert any("doorbell-stop.sh" in c for c in commands), (
        "the router door is not a registered Stop hook"
    )
    from divineos.core import hook_router, hook_surfaces

    hook_router.clear("Stop")
    hook_surfaces.install()
    assert "stall_on_promise" in hook_router.registered("Stop")


def test_the_carve_out_does_not_weaken_the_delta_rule_for_the_work():
    text = retry_scope_text()
    assert "emit the DELTA ONLY" in text
    assert "Do NOT re-issue the work content" in text
