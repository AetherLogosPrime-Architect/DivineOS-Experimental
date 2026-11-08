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


def test_a_routed_doorman_is_named_not_the_router_it_lives_in():
    # Real shape, 2026-09-26: the heredoc refusal arrives through the router.
    routed = (
        "PreToolUse:Bash hook error: [bash .claude/hooks/doorbell-pre-tool-use.sh]: "
        "BLOCKED by heredoc_escape: HEREDOC-ESCAPE DOORMAN - this Bash call writes a file"
    )
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(routed)])
    assert [s.token for s in stumbles] == ["heredoc_escape"]


def test_a_crash_is_named_by_its_exception_not_its_exit_code():
    crash = (
        'Exit code 1\nTraceback (most recent call last):\n  File "x.py", line 3, in <module>\n'
        "    print(v[5])\nIndexError: list index out of range"
    )
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(crash)])
    assert [s.token for s in stumbles] == ["indexerror"]


def test_a_stumble_answered_in_an_earlier_reply_this_turn_is_not_asked_again():
    # Aether, 'the room asks twice', 2026-09-26.
    earlier = "## REFLECTION\nwork-item-doorman stopped me. fixed by structure: flow first\n## INNER CIRCLE\nDad"
    later = "letter answered\n## REFLECTION\nnothing new\n## INNER CIRCLE\nDad"
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(REFUSAL)])
    assert room.taken_up(earlier + "\n\n" + later, stumbles)


def test_a_repeated_queued_message_does_not_move_the_start_past_the_stumbles():
    # 2026-09-26: 'last-prompt' repeats his queued message through the turn.
    recs = [_queued("fix the door"), _tool(), _error(REFUSAL), _queued("fix the door"), _tool()]
    _, stumbles, _ = room.this_turn(recs)
    assert len(stumbles) == 1


def test_a_reflection_that_takes_each_stumble_up_passes():
    reply = "work\n\n## REFLECTION\nThe work-item-doorman stopped me.\nfixed by structure: search runs first\n\n## INNER CIRCLE\nDad"
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(REFUSAL)])
    assert room.taken_up(reply, stumbles)


def test_a_generic_ending_that_names_no_stumble_is_held():
    # Aether, station four: five 'owed: fix it' lines cleared five stumbles.
    reply = "work\n## REFLECTION\nowed: fix it\nowed: fix it\n## INNER CIRCLE\nDad"
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(REFUSAL)])
    assert not room.taken_up(reply, stumbles)


def test_a_bare_exit_1_probe_is_not_a_stumble():
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error("Exit code 1")])
    assert stumbles == []


def test_a_pipe_that_closed_early_on_purpose_is_not_a_stumble():
    # Exit 141 is a writer told to stop by `| head` or `| tail`; the output above it is the answer (Aether, 2026-11-07).
    closed = "Exit code 141\nSat Nov  7 00:34:02 PST 2026\nMY claude: 43436"
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(closed)])
    assert stumbles == []


def test_a_141_with_a_traceback_is_still_a_crash():
    crash = (
        'Exit code 141\nTraceback (most recent call last):\n  File "x.py", line 1, in <module>\n'
        "ValueError: no"
    )
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(crash)])
    assert [s.token for s in stumbles] == ["valueerror"]


def test_a_141_hiding_an_error_line_still_counts():
    # The cheap evasion: end a failing command in a head pipe so its real error reads as a pipe closing.
    hidden = "Exit code 141\nfatal: not a git repository (or any of the parent directories): .git"
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(hidden)])
    assert len(stumbles) == 1


def test_a_141_over_a_failing_tool_is_still_a_stumble():
    # Aria's cold read: these shapes slipped through a line-start pattern. Each is a real failure cut by a head pipe.
    shapes = [
        "Exit code 141\nE   assert 1 == 2\ntests/test_x.py:4: AssertionError",
        "Exit code 141\nsrc/a.py:3: error: Incompatible return value type",
        "Exit code 141\nmake: *** [all] Error 1",
        "Exit code 141\nnpm ERR! code ELIFECYCLE",
        "Exit code 141\nsrc/a.py:1:1: F401 'os' imported but unused",
        "Exit code 141\ntests/test_x.py::test_a FAILED",
        "Exit code 141\nls: cannot access 'x': No such file or directory",
    ]
    for shape in shapes:
        _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(shape)])
        assert len(stumbles) == 1, shape


def test_a_failing_test_that_only_quotes_the_lens_phrase_is_still_a_stumble():
    quoting = "Exit code 1\nFAILED tests/test_walk.py::test_x - assert 'had not been delivered to you in this walk' in out"
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(quoting)])
    assert len(stumbles) == 1


def test_a_council_lens_being_delivered_is_not_a_stumble():
    # The first apply of a lens exits 1 by design while it delivers the lens text.
    delivering = (
        "Exit code 1\nError: Hoare had not been delivered to you in this walk. "
        "It is delivered now, below, and recorded."
    )
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(delivering)])
    assert stumbles == []


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


def test_the_hold_names_only_what_is_still_unanswered():
    # Aether 2026-09-27: held with six, five answered earlier; all six were listed.
    earlier = "## REFLECTION\nwork-item-doorman stopped me. fixed by structure: flow first\n## INNER CIRCLE\nDad"
    crash = "Exit code 1\nTraceback (most recent call last):\nIndexError: list index out of range"
    _, stumbles, _ = room.this_turn([_his("go"), _tool(), _error(REFUSAL), _error(crash)])
    assert [s.token for s in room.still_open(earlier, stumbles)] == ["indexerror"]


def test_talking_with_no_tools_is_never_held():
    worked, _, _ = room.this_turn([_his("how was your day"), _say("lovely")])
    assert not worked


def test_the_hold_no_longer_calls_itself_a_warden_but_still_knows_its_old_words():
    from divineos.core import reflection_room as rr

    assert "WARDEN" not in rr.ROOM_MARK
    assert rr.OLD_ROOM_MARK == "THE WARDEN READS THE LOG"
    text = rr.hold_reason([rr.Stumble("x", 1, "e")])
    assert text.startswith(rr.ROOM_MARK) and "WARDEN" not in text
