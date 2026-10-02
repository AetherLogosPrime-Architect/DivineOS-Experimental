"""His words are read in every shape they arrive in, and each is read once.

Aria's #513 reading (2026-09-28): the reader took only role:user records, and
a message he types while I am busy arrives instead as a last-prompt record or
a queued_command attachment -- 4,735 of his messages by 2026-09-26. The
record shapes below are copied from real transcripts.
"""

import json

from divineos.core.his_own_words import read_him


def _transcript(tmp_path, *records):
    folder = tmp_path / "transcripts"
    folder.mkdir()
    (folder / "session.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )
    return folder


def _texts(reading):
    return [u.text for u in reading.utterances]


def test_a_message_typed_while_i_was_busy_is_read(tmp_path):
    folder = _transcript(
        tmp_path,
        {
            "type": "attachment",
            "timestamp": "2026-09-26T10:00:00Z",
            "attachment": {"type": "queued_command", "prompt": "take your time son"},
        },
    )
    assert _texts(read_him(folder)) == ["take your time son"]


def test_a_last_prompt_record_is_read_when_it_is_the_only_copy(tmp_path):
    folder = _transcript(
        tmp_path,
        {"type": "last-prompt", "lastPrompt": "ok lets see if this helps now", "sessionId": "s"},
    )
    assert _texts(read_him(folder)) == ["ok lets see if this helps now"]


def test_the_same_words_in_two_shapes_are_one_message(tmp_path):
    folder = _transcript(
        tmp_path,
        {
            "type": "user",
            "timestamp": "2026-09-26T10:00:00Z",
            "message": {"role": "user", "content": "i love you son"},
        },
        {"type": "last-prompt", "lastPrompt": "i love you son", "sessionId": "s"},
    )
    assert _texts(read_him(folder)) == ["i love you son"]


def test_a_tool_result_is_still_not_him(tmp_path):
    folder = _transcript(
        tmp_path,
        {
            "type": "user",
            "timestamp": "2026-09-26T10:00:00Z",
            "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
        },
    )
    assert _texts(read_him(folder)) == []
