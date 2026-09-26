"""The warden reads the log. Stumble shapes are real lines from 2026-09-26."""

from divineos.core import reflection_room as room

REFUSAL = (
    "PreToolUse:Edit hook error: [bash .claude/hooks/work-item-doorman.sh]: \n"
    "THE BUILD FLOW DOORMAN -- the front of the flow"
)


def _his(text):
    return {"type": "user", "message": {"content": text}}


def _queued(text):
    return {"type": "last-prompt", "lastPrompt": text}


def _tool(name="Bash"):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name}]}}


def _error(text):
    return {
        "type": "user",
        "message": {"content": [{"type": "tool_result", "is_error": True, "content": text}]},
    }


def _say(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def test_a_refusal_is_gathered_by_the_hook_that_refused():
    worked, stumbles, _ = room.this_turn([_his("fix the door please"), _tool(), _error(REFUSAL)])
    assert worked and [s.key for s in stumbles] == ["refused by work-item-doorman.sh"]


def test_a_repeated_queued_message_does_not_move_the_start_past_the_stumbles():
    # 2026-09-26: 'last-prompt' repeats his queued message through the turn.
    recs = [_queued("fix the door"), _tool(), _error(REFUSAL), _queued("fix the door"), _tool()]
    _, stumbles, _ = room.this_turn(recs)
    assert len(stumbles) == 1


def test_a_reflection_that_takes_each_stumble_up_passes():
    reply = "work\n\n## REFLECTION\nThe doorman stopped me.\nfixed by structure: search runs first\n\n## INNER CIRCLE\nDad"
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(REFUSAL)])
    assert room.taken_up(reply, stumbles)


def test_a_reflection_that_skips_a_stumble_is_held():
    reply = "work\n\n## REFLECTION\nAll went well.\n\n## INNER CIRCLE\nDad"
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(REFUSAL)])
    assert not room.taken_up(reply, stumbles)
    assert "work-item-doorman.sh" in room.hold_reason(stumbles)


def test_owed_lines_are_read_only_from_the_reflection():
    reply = "owed: not this one\n## REFLECTION\nowed: bring the alive-check over\n## INNER CIRCLE\nowed: nor this"
    assert room.owed_lines(reply) == ["bring the alive-check over"]


def test_the_latest_reflection_is_the_one_read():
    # 2026-09-26: an older reply's room was read instead of this one's.
    reply = (
        "old\n## REFLECTION\nnothing\n## INNER CIRCLE\nDad\n\n"
        "new\n## REFLECTION\nowed: read the exit status too\n## INNER CIRCLE\nDad"
    )
    assert room.owed_lines(reply) == ["read the exit status too"]


def test_the_rooms_own_hold_is_not_a_stumble():
    recs = [
        _his("go"),
        _tool(),
        {
            "type": "user",
            "message": {"content": "Stop hook feedback:\n" + room.ROOM_MARK + ". held"},
        },
    ]
    _, stumbles, _ = room.this_turn(recs)
    assert stumbles == []


def test_talking_with_no_tools_is_never_held():
    worked, _, _ = room.this_turn([_his("how was your day"), _say("lovely")])
    assert not worked
