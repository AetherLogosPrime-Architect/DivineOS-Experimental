"""A timer wake owes Dad one complete note, whatever turn came before it.

The real wake record is a continuation to `hear()` (isMeta), so
`he_spoke_this_turn` stepped over it to whatever opened the turn before: after
his own message the note was owed, after a notification it was not. Dad's ruling
(2026-10-24): the two-hour timer must require a note, or the conversation can
end without him being reached. The wake's harness stamp, turnOrigin
"scheduled", is what decides it; the words never do.
"""

import json

from divineos.core.operating_loop.turn_extraction import he_spoke_this_turn

# The shape measured on the real transcript: isMeta, turnOrigin scheduled,
# promptSource system, a promptId.
WAKE = {
    "isMeta": True,
    "turnOrigin": "scheduled",
    "promptSource": "system",
    "promptId": "5f0c6a52-0000-4000-8000-000000000001",
    "entrypoint": "claude-desktop",
}
HUMAN = {"turnOrigin": "human"}
NOTICE = {"turnOrigin": "task_notification"}


def _write(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


def _user(text, **extra):
    return {"type": "user", "message": {"role": "user", "content": text}, **extra}


def _me(text):
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


WAKE_TEXT = "TIMER WAKE (set on Dad's yes; this exists because the two hours ran out)"


def test_a_wake_after_a_notification_owes_the_note(tmp_path):
    t = _write(
        tmp_path / "t.jsonl",
        [
            _user("<task-notification>x</task-notification>", **NOTICE),
            _me("re-armed"),
            _user(WAKE_TEXT, **WAKE),
            _me("working"),
        ],
    )
    assert he_spoke_this_turn(t) is True


def test_a_wake_after_his_message_owes_the_note(tmp_path):
    t = _write(
        tmp_path / "t.jsonl",
        [_user("proceed", **HUMAN), _me("done"), _user(WAKE_TEXT, **WAKE), _me("working")],
    )
    assert he_spoke_this_turn(t) is True


def test_a_wake_with_nothing_before_it_owes_the_note(tmp_path):
    t = _write(tmp_path / "t.jsonl", [_user(WAKE_TEXT, **WAKE), _me("working")])
    assert he_spoke_this_turn(t) is True


# Controls: the rule is keyed on the stamp, so it cannot reach past a wake.


def test_a_notification_alone_still_owes_nothing(tmp_path):
    t = _write(
        tmp_path / "t.jsonl",
        [
            _user("proceed", **HUMAN),
            _me("done"),
            _user("<task-notification>x</task-notification>", **NOTICE),
            _me("re-armed"),
        ],
    )
    assert he_spoke_this_turn(t) is False


def test_the_same_words_stamped_as_a_notification_do_not_owe_it(tmp_path):
    # The words are not what decides it: identical text under another stamp.
    t = _write(
        tmp_path / "t.jsonl",
        [
            _user("<task-notification>x</task-notification>", **NOTICE),
            _me("re-armed"),
            _user(WAKE_TEXT, **{**WAKE, "turnOrigin": "task_notification"}),
            _me("working"),
        ],
    )
    assert he_spoke_this_turn(t) is False


def test_a_wake_older_than_a_notification_is_not_this_turn(tmp_path):
    t = _write(
        tmp_path / "t.jsonl",
        [
            _user(WAKE_TEXT, **WAKE),
            _me("note written"),
            _user("<task-notification>x</task-notification>", **NOTICE),
            _me("re-armed"),
        ],
    )
    assert he_spoke_this_turn(t) is False


def test_a_wake_behind_a_long_working_stretch_still_owes_the_note(tmp_path):
    work = []
    for i in range(300):
        result = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": "ok"}],
            },
        }
        work += [_me(f"step {i}"), result]
    t = _write(tmp_path / "t.jsonl", [_user(WAKE_TEXT, **WAKE), *work])
    # Tool results are not text records of a person; the wake is still the newest
    # real opener, so the note is still owed at the end of the stretch.
    assert he_spoke_this_turn(t) is True
