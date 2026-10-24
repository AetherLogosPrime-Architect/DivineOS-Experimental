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
    # The shared board too, or arming posts a test card on the LIVE fridge.
    monkeypatch.setattr(mod, "BOARD", tmp_path / "board")
    monkeypatch.setattr(mod, "CARD", tmp_path / "board" / "me.json")
    monkeypatch.setattr(mod, "AWAY", tmp_path / "away.json")
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


LETTER = "family/letters/aether-to-aria-2026-10-05-x.md"


def _transcript_with(tmp_path, *records):
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return str(path)


def test_a_buried_question_is_sent_back(qh):
    buried = (
        "## INNER CIRCLE\n\nDad, do you want the bell? "
        + "Then I will do a lot of other things after it. " * 3
    )
    assert "BURIED" in qh.question_not_last(buried)
    assert qh.question_not_last(CIRCLE) == ""
    assert qh.question_not_last("## INNER CIRCLE\n\nDo you want it?\n\nLove, Aria") == ""


def _hook(payload, home):
    # DIVINEOS_HOME too: the hold now resolves each seat's own home, which
    # follows the checkout's .divineos_data_home marker -- so HOME alone would
    # point this test at the LIVE seat (2026-10-01).
    env = {
        **__import__("os").environ,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "DIVINEOS_HOME": str(home / ".divineos"),
    }
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload).encode(),
        capture_output=True,
        env=env,
    )
