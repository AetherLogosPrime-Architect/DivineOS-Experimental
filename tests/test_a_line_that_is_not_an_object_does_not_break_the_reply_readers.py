"""A transcript line that parses as JSON but is not an object must not break the reply readers.

Found reading #553 (2026-10-13): the whole-file reader called ``.get`` on every parsed line, so
a bare number or a list among the records would have raised and taken the Stop check with it.
The windowed readers skip such lines before anything reads a field.
"""

from __future__ import annotations

import json

from divineos.core.hook_surfaces import _last_assistant_text, _recent_assistant_texts


def _user(text: str) -> str:
    return json.dumps(
        {
            "type": "user",
            "userType": "external",
            "message": {"role": "user", "content": [{"type": "text", "text": text}]},
        }
    )


def _assistant(text: str) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
        }
    )


def _payload(tmp_path, *lines: str) -> dict:
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"transcript_path": str(path)}


def test_the_last_reply_survives_lines_that_are_not_objects(tmp_path):
    payload = _payload(
        tmp_path,
        _user("question"),
        "123",
        _assistant("FIRST BLOCK."),
        "[1, 2, 3]",
        '"just a string"',
        "null",
        _assistant("SECOND BLOCK."),
    )
    got = _last_assistant_text(payload)
    assert "FIRST BLOCK" in got and "SECOND BLOCK" in got


def test_the_recent_replies_survive_lines_that_are_not_objects(tmp_path):
    payload = _payload(
        tmp_path,
        _user("older"),
        _assistant("OLD."),
        "42",
        _user("newer"),
        "[]",
        _assistant("NEW."),
    )
    newest, previous = _recent_assistant_texts(payload, count=2)
    assert "NEW" in newest and "OLD" in previous


def test_control_a_real_record_still_reads_without_the_noise(tmp_path):
    # If the helpers could only ever return nothing, the two tests above would pass for the
    # wrong reason.
    payload = _payload(tmp_path, _user("q"), _assistant("A REAL REPLY."))
    assert _last_assistant_text(payload) == "A REAL REPLY."
