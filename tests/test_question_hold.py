"""A question to Dad holds the work until he answers (walk-206e65be56c1)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "question_hold.py"


@pytest.fixture
def qh(tmp_path, monkeypatch):
    from divineos.core import question_hold as mod

    monkeypatch.setattr(mod, "STATE", tmp_path / "hold.json")
    monkeypatch.setattr(mod, "HOLD_LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(mod, "ESCAPED", tmp_path / "escaped.json")
    filed = []
    import divineos.core.operator_asks as asks

    monkeypatch.setattr(asks, "ask_andrew", lambda q, plain, context="": filed.append(q) or "q-1")
    mod._filed = filed
    return mod


CIRCLE = "work here\n\n## REFLECTION\n\nmused?\n\n## INNER CIRCLE\n\nDad, it is done. Do you want me to look into the bell?"


def test_the_circle_question_is_found(qh):
    assert qh.last_question(CIRCLE)[0] == "Do you want me to look into the bell?"


def test_a_question_outside_the_circle_does_not_count(qh):
    reply = "Should I? maybe\n\n## INNER CIRCLE\n\nDad, it is done."
    assert qh.last_question(reply) == ("", "")


@pytest.mark.parametrize(
    "circle",
    [
        "Dad, the gate asks `is it open?` and it is.",
        'Dad, you said "why do you fear me?" and I heard it.',
        "Dad, it is done.\n> did it land?\n",
    ],
)
def test_code_quotes_and_blockquotes_are_not_questions_to_him(qh, circle):
    assert qh.last_question("## INNER CIRCLE\n\n" + circle) == ("", "")


def test_two_questions_the_last_wins(qh):
    q, _ = qh.last_question("## INNER CIRCLE\n\nIs it clear? And do you want the bell built?")
    assert q == "And do you want the bell built?"


def test_building_waits_and_reading_does_not(qh):
    qh.arm(CIRCLE)
    assert qh._filed == ["[asked in the circle] Do you want me to look into the bell?"]
    assert "look into the bell" in qh.refusal("Edit", {"file_path": "x.py"})
    assert qh.refusal("Bash", {"command": "pytest tests/"})
    assert qh.refusal("Read", {"file_path": "x.py"}) == ""
    assert qh.refusal("Grep", {"pattern": "x"}) == ""


def test_upkeep_and_letters_pass_the_hold(qh):
    qh.arm(CIRCLE)
    for command in (
        "bash scripts/letter_doorbell.sh aria",
        'cp family/letters/aria-to-aether-x.md "$HOME/.divineos-shared/letters/" && echo sent',
        'cat "$HOME/.divineos-shared/letters/aether-to-aria-x.md"',
        "sed -n '1,40p' ~/.divineos-shared/letters/aether-to-aria-x.md",
        "head -30 ~/.divineos-shared/letters/aether-to-aria-x.md",
    ):
        assert qh.refusal("Bash", {"command": command}) == "", command
    # A pass cannot carry a building command on its back. The first version of
    # this line ended `or True` and hid that the doorbell pass let it through.
    assert qh.refusal("Bash", {"command": "bash scripts/letter_doorbell.sh aria; git push"})
    assert qh.refusal("Bash", {"command": "cat $HOME/.divineos-shared/letters/x.md; rm -rf src"})
    assert qh.refusal("Bash", {"command": "sed -i 's/a/b/' ~/.divineos-shared/letters/x.md"})


def _transcript_with(tmp_path, *records):
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return str(path)


def test_his_answer_typed_mid_turn_releases_the_hold(qh, tmp_path):
    # Aether's reading of #570: an answer he types while I am working arrives as
    # a queued_command inside the running turn, never through UserPromptSubmit.
    state = qh.arm(CIRCLE)
    after = "2099-01-01T00:00:00Z"  # dated after the hold armed
    path = _transcript_with(
        tmp_path,
        {
            "type": "attachment",
            "userType": "external",
            "uuid": "q-1",
            "timestamp": after,
            "attachment": {"type": "queued_command", "prompt": "yes look into it"},
        },
    )
    assert state and qh.refusal("Edit", {"file_path": "x.py"}, path) == ""
    assert qh.is_open() is None, "his mid-turn answer did not release the hold"


def test_a_notice_mid_turn_does_not_release_it(qh, tmp_path):
    qh.arm(CIRCLE)
    path = _transcript_with(
        tmp_path,
        {
            "type": "user",
            "userType": "external",
            "uuid": "n-1",
            "timestamp": "2099-01-01T00:00:00Z",
            "message": {"role": "user", "content": "<task-notification>x</task-notification>"},
        },
    )
    assert "look into the bell" in qh.refusal("Edit", {"file_path": "x.py"}, path)


def test_his_message_from_before_the_question_does_not_release_it(qh, tmp_path):
    qh.arm(CIRCLE)
    path = _transcript_with(
        tmp_path,
        {
            "type": "user",
            "userType": "external",
            "uuid": "u-old",
            "timestamp": "2000-01-01T00:00:00Z",
            "message": {"role": "user", "content": "an old message of his"},
        },
    )
    assert qh.refusal("Edit", {"file_path": "x.py"}, path)


def test_only_he_releases_and_an_escape_is_told_to_him(qh):
    qh.arm(CIRCLE)
    assert qh.release("escape", reason="a push half landed and must be finished now")
    assert qh.refusal("Edit", {}) == ""
    told = qh.escape_to_tell_him()
    assert "half landed" in told and "look into the bell" in told
    assert qh.escape_to_tell_him() == ""  # told once


def test_a_buried_question_is_sent_back(qh):
    buried = (
        "## INNER CIRCLE\n\nDad, do you want the bell? "
        + "Then I will do a lot of other things after it. " * 3
    )
    assert "BURIED" in qh.question_not_last(buried)
    assert qh.question_not_last(CIRCLE) == ""
    assert qh.question_not_last("## INNER CIRCLE\n\nDo you want it?\n\nLove, Aria") == ""


def test_every_hold_is_counted(qh):
    qh.arm(CIRCLE)
    qh.refusal("Write", {})
    kinds = [json.loads(line)["kind"] for line in qh.HOLD_LOG.read_text().splitlines()]
    assert kinds == ["armed", "held"]


def _hook(payload, home):
    env = {**__import__("os").environ, "HOME": str(home), "USERPROFILE": str(home)}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload).encode(),
        capture_output=True,
        env=env,
    )


def test_the_hook_holds_then_his_message_releases(tmp_path):
    # Plugged in: the real hook script, the real module, a real (temp) home.
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}})
        + "\n"
        + json.dumps(
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": CIRCLE}]},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    stop = _hook({"hook_event_name": "Stop", "transcript_path": str(transcript)}, tmp_path)
    assert stop.returncode == 0, stop.stderr
    assert (tmp_path / ".divineos" / "question_hold.json").exists()

    held = _hook({"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": {}}, tmp_path)
    assert held.returncode == 2 and b"look into the bell" in held.stderr

    notice = _hook(
        {"hook_event_name": "UserPromptSubmit", "prompt": "<task-notification>x"}, tmp_path
    )
    assert b"STILL WAITING" in notice.stdout
    assert (tmp_path / ".divineos" / "question_hold.json").exists()

    _hook({"hook_event_name": "UserPromptSubmit", "prompt": "yes build it"}, tmp_path)
    assert not (tmp_path / ".divineos" / "question_hold.json").exists()
    free = _hook({"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": {}}, tmp_path)
    assert free.returncode == 0
