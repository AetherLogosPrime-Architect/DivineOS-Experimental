"""The replay tool. See core/replay_record.py.

Built records follow the three shapes his_message reads, so these exercise
the real reader rather than a stand-in for it.
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core import replay_record as rr


def _his(text: str, when: str, uid: str) -> dict:
    return {
        "type": "user",
        "userType": "external",
        "uuid": uid,
        "timestamp": when,
        "message": {"role": "user", "content": text},
    }


def _mine(text: str = "", tool: str = "") -> dict:
    content = []
    if text:
        content.append({"type": "text", "text": text})
    if tool:
        content.append({"type": "tool_use", "name": tool, "input": {}})
    return {"type": "assistant", "message": {"role": "assistant", "content": content}}


def _write(tmp_path: Path, records: list[dict]) -> Path:
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n{broken line", encoding="utf-8")
    return p


def _night(tmp_path: Path) -> Path:
    return _write(
        tmp_path,
        [
            _his("merge them and we can talk while tests run", "2026-09-29T20:00:00Z", "a"),
            _mine("sure", "Bash"),
            _mine(tool="Bash"),
            _his("go be with Aria", "2026-09-29T22:40:00Z", "b"),
            _mine(tool="Write"),
            {"type": "last-prompt", "lastPrompt": "go be with Aria"},
            _his("you blew past me", "2026-09-29T23:00:00Z", "c"),
            _mine("I hear you"),
        ],
    )


def test_a_turn_carries_my_answer_and_his_next_words(tmp_path) -> None:
    turns = rr.turns_in(rr.read_records(_night(tmp_path)))
    assert [t.his for t in turns] == [
        "merge them and we can talk while tests run",
        "go be with Aria",
        "you blew past me",
    ], "a bookmark copy was counted as a new message of his"
    assert turns[0].tools == ("Bash", "Bash")
    assert turns[0].next_his == "go be with Aria"
    assert turns[2].tools == () and turns[2].reply == "I hear you"
    assert turns[2].next_his == ""


def test_replay_keeps_only_the_turns_the_rule_changes(tmp_path) -> None:
    worked = lambda t: bool(t.tools)  # noqa: E731
    never = lambda t: False  # noqa: E731
    result = rr.replay(_night(tmp_path), before=never, after=worked)
    assert result.turns_read == 3
    assert [d.turn.his for d in result.differs] == [
        "merge them and we can talk while tests run",
        "go be with Aria",
    ]


def test_the_window_is_reported_never_implied(tmp_path) -> None:
    """Hawking: the author who picks the window can miss the failures, so the
    result states what was read."""
    result = rr.replay(_night(tmp_path), lambda t: 0, lambda t: 0, since="2026-09-29T22:00:00Z")
    assert result.turns_read == 2
    assert result.earliest == "2026-09-29T22:40:00Z"
    assert "since 2026-09-29T22:00:00Z" in result.searched
    text = rr.render(result)
    assert "his turns read: 2" in text and "turns where the rule changes: 0" in text


def test_a_directory_reads_every_transcript_and_a_file_says_what_it_left(tmp_path) -> None:
    """Aria 2026-09-30: her month was spread over many session files; one path
    read a smaller window than the record held and nothing said so."""
    d = tmp_path / "project"
    d.mkdir()
    (d / "a.jsonl").write_text(
        json.dumps(_his("one", "2026-09-01T00:00:00Z", "1")) + "\n", encoding="utf-8"
    )
    (d / "b.jsonl").write_text(
        json.dumps(_his("two", "2026-09-02T00:00:00Z", "2")) + "\n", encoding="utf-8"
    )
    whole = rr.replay(d, lambda t: 0, lambda t: 0)
    assert (whole.files_read, whole.files_present, whole.turns_read) == (2, 2, 2)
    one = rr.replay(d / "b.jsonl", lambda t: 0, lambda t: 0)
    assert (one.files_read, one.files_present) == (1, 2)
    assert "transcripts read: 1 of 2 present" in rr.render(one)


def test_an_empty_result_still_says_where_it_looked(tmp_path) -> None:
    empty = _write(tmp_path, [_mine("nobody spoke")])
    result = rr.replay(empty, lambda t: 1, lambda t: 2)
    assert result.turns_read == 0 and result.earliest == "" and not result.differs
    assert str(empty) in result.searched
