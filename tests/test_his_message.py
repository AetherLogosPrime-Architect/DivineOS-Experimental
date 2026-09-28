"""One reader of him: every shape heard, each message once, the machine refused.

Record shapes are copied from real transcripts (2026-09-28). The last test runs
the reader over the real transcript folder when there is one, so the single
reader everything leans on has an alarm of its own.
"""

import json
from pathlib import Path

import pytest

from divineos.core.his_message import Heard, Unclassified, hear, heard_in

TYPED = {
    "type": "user",
    "userType": "external",
    "uuid": "u-1",
    "timestamp": "2026-09-28T10:00:00Z",
    "message": {"role": "user", "content": "ok lets keep working through them"},
}
QUEUED = {
    "type": "attachment",
    "userType": "external",
    "uuid": "u-2",
    "timestamp": "2026-09-28T10:01:00Z",
    "attachment": {"type": "queued_command", "prompt": "hold 5"},
}
BOOKMARK = {
    "type": "last-prompt",
    "lastPrompt": "ok lets keep working through them",
    "sessionId": "s",
}


def test_a_message_he_typed_is_heard():
    assert hear(TYPED) == Heard("ok lets keep working through them", "u-1", "2026-09-28T10:00:00Z")


def test_a_line_he_typed_while_i_was_busy_is_heard():
    got = hear(QUEUED)
    assert isinstance(got, Heard) and got.text == "hold 5"


def test_a_bookmark_is_his_words_and_marked_as_a_copy():
    got = hear(BOOKMARK)
    assert isinstance(got, Heard) and got.bookmark


@pytest.mark.parametrize(
    "record",
    [
        {**TYPED, "isMeta": True},
        {**TYPED, "isSidechain": True},
        {**TYPED, "isCompactSummary": True},
        {
            **TYPED,
            "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
        },
        {
            **TYPED,
            "message": {"role": "user", "content": "<task-notification>\n<task-id>x</task-id>"},
        },
        {**TYPED, "message": {"role": "user", "content": "Stop hook feedback:\nTHE WARDEN"}},
        {"type": "assistant", "message": {"role": "assistant", "content": "mine"}},
    ],
    ids=[
        "hook-notice",
        "subagent",
        "compaction",
        "tool-result",
        "task-notice",
        "stop-feedback",
        "me",
    ],
)
def test_the_machine_in_his_seat_is_not_him(record):
    assert hear(record) is None


def test_a_message_of_his_that_opens_with_caveat_is_still_his():
    record = {**TYPED, "message": {"role": "user", "content": "Caveat: i might be wrong but"}}
    assert isinstance(hear(record), Heard)


def test_an_external_record_in_no_known_shape_is_reported_not_dropped():
    assert isinstance(hear({"type": "user", "userType": "external"}), Unclassified)


def test_each_message_is_heard_once_and_a_repeat_of_his_is_kept():
    again = {**TYPED, "uuid": "u-3", "timestamp": "2026-09-28T11:00:00Z"}
    heard = heard_in([TYPED, TYPED, QUEUED, BOOKMARK, again])
    assert [h.text for h in heard] == [
        "ok lets keep working through them",
        "hold 5",
        "ok lets keep working through them",
    ]


def test_messages_without_a_record_id_are_never_merged():
    one = {"type": "user", "message": {"role": "user", "content": "first"}}
    two = {"type": "user", "message": {"role": "user", "content": "second"}}
    assert [h.text for h in heard_in([one, two])] == ["first", "second"]


def test_a_bookmark_is_kept_when_it_is_the_only_copy():
    lone = {"type": "last-prompt", "lastPrompt": "are you there?"}
    assert [h.text for h in heard_in([lone])] == ["are you there?"]


def test_on_the_real_transcripts_every_shape_is_found():
    root = Path.home() / ".claude" / "projects"
    paths = sorted(root.glob("*/*.jsonl"))[:200] if root.is_dir() else []
    if not paths:
        pytest.skip("no real transcripts on this machine")
    kinds = {"typed": 0, "queued": 0, "bookmark": 0}
    for path in paths:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            got = hear(record)
            if not isinstance(got, Heard):
                continue
            if got.bookmark:
                kinds["bookmark"] += 1
            elif (record.get("attachment") or {}).get("type") == "queued_command":
                kinds["queued"] += 1
            else:
                kinds["typed"] += 1
    assert all(kinds.values()), f"a shape of his went unheard: {kinds}"
