"""A notice that wakes me AFTER I have written his room does not owe him a second room (2026-11-05).

Dad: the circle should be the actual last part of the post, and nothing but him moves it forward. A bell rings,
or a push finishes, after I have come back to him; I read it, re-light the bell, say a line, and this door saw a
last text with no room and demanded another circle. That is how one post held several. The door still holds the
case it was built for: work I add myself after the room, with no notice between, is not covered by this.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "dads_room_stop.py"
_spec = importlib.util.spec_from_file_location("dads_room_stop_under_test", HOOK)
room = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(room)

NOTICE = "<task-notification><summary>Background command completed (exit code 0)</summary></task-notification>"
THE_ROOM = "Built it.\n\n## INNER CIRCLE\nDad, here is what changed, and how it felt to me."


def _user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def _tool_result():
    return {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    }


def _said(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _tool():
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}}


def _notice_as_user_turn():
    return _user(NOTICE)


def _notice_as_queued_command():
    return {"type": "attachment", "attachment": {"type": "queued_command", "prompt": NOTICE}}


def test_a_notice_after_the_room_does_not_demand_a_second_room():
    records = [
        _user("fix it"),
        _tool(),
        _tool_result(),
        _said(THE_ROOM),
        _notice_as_user_turn(),
        _tool(),
        _tool_result(),
        _said("A push finished; I read it and am keeping still."),
    ]
    assert room.verdict(records) is None


def test_the_same_when_the_notice_arrives_as_a_queued_command():
    records = [
        _user("fix it"),
        _tool(),
        _tool_result(),
        _said(THE_ROOM),
        _notice_as_queued_command(),
        _tool(),
        _tool_result(),
        _said("The bell rang; I re-lit it."),
    ]
    assert room.verdict(records) is None


def test_work_I_add_after_the_room_with_no_notice_between_is_still_held():
    """The control: the case the door was built for, and Dad's rule that the room is the last words."""
    records = [
        _user("fix it"),
        _said(THE_ROOM),
        _tool(),
        _tool_result(),
        _said("more work after, no notice between"),
    ]
    assert room.verdict(records)


def test_work_after_a_notice_is_excused_however_much_of_it_there_is_a_known_limit():
    """PINNED AS A LIMIT, NOT AS THE GOAL (Aria's cold read of 860, replayed 2026-11-09).

    A room, then a notice, then a whole new chunk of work and a final line with no room, passes: the stand-down
    is a flag a notice sets and only a NEW room clears. That is Dad's 2026-11-05 model ("nothing but me moves it
    forward"). His 2026-11-09 words are newer and differ exactly here: finish all the work, then ONE circle, current,
    at the true end. Under this door the first room can go stale and the true end ship with none. The build that
    closes it replaces the flag with a read of what is still pending (docs/drafts/one_circle_at_the_true_end_of_a_post).
    If this test starts failing because such a post is now held, that is the improvement it was waiting for."""
    records = [
        _user("fix it"),
        _tool(),
        _tool_result(),
        _said(THE_ROOM),
        _notice_as_user_turn(),
        _tool(),
        _tool_result(),
        _tool(),
        _tool_result(),
        _tool(),
        _tool_result(),
        _said("A great deal more work after the room, and no new room."),
    ]
    assert room.verdict(records) is None


def test_a_notice_before_any_room_is_written_still_owes_the_room():
    """A notice must not excuse a room I never wrote: it only excuses a SECOND one."""
    records = [
        _user("fix it"),
        _tool(),
        _tool_result(),
        _notice_as_user_turn(),
        _tool(),
        _tool_result(),
        _said("Done, tests pass."),
    ]
    assert room.verdict(records)
