"""While he is away a closing question goes to the morning list and nothing waits (Dad, 2026-10-12).

"no questions to him in chat; they go in the morning letter". The cases are the real shapes of away:
his own words saying he is going to bed, two hours of silence, and the midnight window with him
chatting and with him quiet. The control that matters most is that while he is HERE a question
still opens the hold exactly as before: a bug that carried questions while he was present would be
silent and look like good manners. Real rows in a real temporary store; the judge is never mocked.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path

import pytest

ASKED = "work\n\n## INNER CIRCLE\n\nDad, should the night window start at ten?"
ASKED_AGAIN = "more work\n\n## INNER CIRCLE\n\nDad, should the night window start at ten?"
OTHER = "work\n\n## INNER CIRCLE\n\nDad, which colour do you want for the felt?"
SCHEDULE = {"his_words": "", "since": 0.0, "by": "schedule"}


@pytest.fixture
def qh(tmp_path, monkeypatch):
    from divineos.core import question_hold as mod

    monkeypatch.setattr(mod, "STATE", tmp_path / "hold.json")
    monkeypatch.setattr(mod, "HOLD_LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(mod, "ESCAPED", tmp_path / "escaped.json")
    monkeypatch.setattr(mod, "AWAY", tmp_path / "away.json")
    monkeypatch.setattr(mod, "MORNING", tmp_path / "morning.jsonl")
    monkeypatch.setattr(mod, "BOARD", tmp_path / "board")
    monkeypatch.setattr(mod, "CARD", tmp_path / "board" / "me.json")
    return mod


def _store(tmp_path, monkeypatch, rows):
    """A his-asks store holding (text, seconds_ago) rows."""
    db = tmp_path / "asks.db"
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    conn = sqlite3.connect(db)
    conn.execute("DROP TABLE IF EXISTS messages")
    conn.execute("CREATE TABLE messages (his_text TEXT, filed_at REAL)")
    now = time.time()
    for text, ago in rows:
        conn.execute("INSERT INTO messages VALUES (?, ?)", (text, now - ago))
    conn.commit()
    conn.close()


def _carried(qh):
    return [r["question"] for r in qh._morning_lines() if r.get("kind") == "carried"]


def test_his_own_words_going_to_bed_carry_the_question_and_nothing_waits(qh, tmp_path, monkeypatch):
    _store(tmp_path, monkeypatch, [("im going to bed, you two volley", 30)])
    qh.step_away("going to bed, you two volley")
    assert qh.arm(ASKED) is None
    assert _carried(qh) == ["Dad, should the night window start at ten?"]
    assert qh.is_open() is None  # no hold
    assert not (tmp_path / "board" / "me.json").exists()  # no card on the shared board


def test_three_hours_without_a_word_carries_the_question(qh, tmp_path, monkeypatch):
    _store(tmp_path, monkeypatch, [("ok go ahead", 3 * 3600)])
    assert qh.arm(ASKED) is None
    assert _carried(qh) == ["Dad, should the night window start at ten?"]
    assert qh.is_open() is None


def test_while_he_is_here_a_question_still_opens_the_hold_as_before(qh, tmp_path, monkeypatch):
    """The control. Ten minutes of quiet is here, and nothing is carried."""
    _store(tmp_path, monkeypatch, [("ok go ahead", 600)])
    state = qh.arm(ASKED)
    assert state and state["question"] == "Dad, should the night window start at ten?"
    assert qh.is_open() is not None
    assert _carried(qh) == []


def test_the_clock_with_him_chatting_does_not_carry_a_live_question(qh, tmp_path, monkeypatch):
    """Midnight to six counts as away for letters even when he is up chatting; for a question it
    would send a live question to a morning he is not waiting for."""
    monkeypatch.setattr(qh, "_scheduled_away", lambda now=None: dict(SCHEDULE))
    _store(tmp_path, monkeypatch, [("whats the plan", 5 * 60)])
    assert qh.arm(ASKED)  # held, as if he were here
    assert _carried(qh) == []


def test_the_clock_with_him_quiet_for_an_hour_carries_it(qh, tmp_path, monkeypatch):
    monkeypatch.setattr(qh, "_scheduled_away", lambda now=None: dict(SCHEDULE))
    _store(tmp_path, monkeypatch, [("night", 3600)])
    assert qh.arm(ASKED) is None
    assert _carried(qh) == ["Dad, should the night window start at ten?"]


def test_a_message_i_could_not_read_is_never_away_so_the_question_is_held(
    qh, tmp_path, monkeypatch
):
    monkeypatch.setattr(qh, "_scheduled_away", lambda now=None: dict(SCHEDULE))
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(tmp_path / "no-such-store.db"))
    assert qh.arm(ASKED)
    assert _carried(qh) == []


def test_a_reply_that_asks_nothing_carries_nothing(qh, tmp_path, monkeypatch):
    _store(tmp_path, monkeypatch, [("ok", 3 * 3600)])
    assert qh.arm("Done. Nothing to ask.") is None
    assert _carried(qh) == [] and not qh.MORNING.exists()


def test_a_list_that_cannot_be_written_falls_back_to_the_hold_and_loses_nothing(
    qh, tmp_path, monkeypatch
):
    _store(tmp_path, monkeypatch, [("ok", 3 * 3600)])
    blocker = tmp_path / "a-file-where-a-folder-should-be"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(qh, "MORNING", blocker / "morning.jsonl")
    assert qh.arm(ASKED)  # held
    assert qh.is_open() is not None
    log = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert any(row["kind"] == "carry_failed" for row in log)


def test_the_same_question_asked_twice_is_carried_once(qh, tmp_path, monkeypatch):
    _store(tmp_path, monkeypatch, [("ok", 3 * 3600)])
    qh.arm(ASKED)
    qh.arm(ASKED_AGAIN)
    assert _carried(qh) == ["Dad, should the night window start at ten?"]


def test_two_different_questions_are_both_carried_oldest_first(qh, tmp_path, monkeypatch):
    _store(tmp_path, monkeypatch, [("ok", 3 * 3600)])
    qh.arm(ASKED)
    qh.arm(OTHER)
    assert [r["question"] for r in qh.overnight_questions()] == [
        "Dad, should the night window start at ten?",
        "Dad, which colour do you want for the felt?",
    ]


class TestWhenHeSpeaks:
    def test_what_i_asked_overnight_is_shown_once_with_the_one_or_two_rule(
        self, qh, tmp_path, monkeypatch
    ):
        _store(tmp_path, monkeypatch, [("ok", 3 * 3600)])
        qh.arm(ASKED)
        shown = qh.morning_surface()
        assert "QUESTIONS I CARRIED FOR HIM" in shown
        assert "should the night window start at ten?" in shown
        assert "one or two" in shown
        assert qh.morning_surface() == ""  # once, never wallpaper
        assert qh.overnight_questions() == []

    def test_nothing_carried_says_nothing(self, qh):
        assert qh.morning_surface() == ""

    def test_shown_questions_stay_readable_for_the_letter_for_a_day(
        self, qh, tmp_path, monkeypatch
    ):
        _store(tmp_path, monkeypatch, [("ok", 3 * 3600)])
        qh.arm(ASKED)
        qh.morning_surface()
        assert [r["question"] for r in qh.carried_lately()] == [
            "Dad, should the night window start at ten?"
        ]
        assert qh.carried_lately(within=-1) == []  # a window that has passed holds nothing

    def test_a_half_written_last_line_is_skipped_not_fatal(self, qh, tmp_path, monkeypatch):
        _store(tmp_path, monkeypatch, [("ok", 3 * 3600)])
        qh.arm(ASKED)
        with qh.MORNING.open("a", encoding="utf-8") as fh:
            fh.write(
                '{"kind": "carried", "id": "9", "at": 1.0, "ques'
            )  # a process killed mid-write
        assert [r["question"] for r in qh.overnight_questions()] == [
            "Dad, should the night window start at ten?"
        ]

    def test_a_shown_mark_that_cannot_be_written_means_shown_again_not_lost(
        self, qh, tmp_path, monkeypatch
    ):
        _store(tmp_path, monkeypatch, [("ok", 3 * 3600)])
        qh.arm(ASKED)
        real_open = Path.open

        def refuse_append(self, mode="r", *a, **k):
            if self == qh.MORNING and "a" in mode:
                raise OSError("disk full")
            return real_open(self, mode, *a, **k)

        monkeypatch.setattr(Path, "open", refuse_append)
        assert "QUESTIONS I CARRIED" in qh.morning_surface()
        monkeypatch.setattr(Path, "open", real_open)
        assert len(qh.overnight_questions()) == 1  # still pending: shown again, never lost


def test_each_seat_has_its_own_list_by_having_its_own_home():
    """The list sits beside the hold's own state in the seat's home, so one seat's question
    cannot land in the other's morning letter."""
    from divineos.core import question_hold as mod

    assert mod.MORNING.parent == mod.STATE.parent
    assert mod.MORNING.name == "morning_questions.jsonl"


def test_the_hook_prints_the_list_on_his_real_message_and_not_on_a_notice():
    """Wiring, read from the hook's own source (the hook runs in its own process): the surface is
    called in the UserPromptSubmit branch that only runs for a real message, after came_back."""
    src = (
        Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "question_hold.py"
    ).read_text(encoding="utf-8")
    branch = src[src.index("if not notice:") : src.index("waiting = qh.others_waiting()")]
    assert "qh.came_back()" in branch and "qh.morning_surface()" in branch
    assert re.search(r"came_back\(\).*morning_surface\(\)", branch, re.S)


def test_the_morning_command_lists_what_was_carried(qh, tmp_path, monkeypatch):
    from click.testing import CliRunner

    import click

    from divineos.cli.question_hold_commands import register

    _store(tmp_path, monkeypatch, [("ok", 3 * 3600)])
    qh.arm(ASKED)
    group = click.Group("divineos")
    register(group)
    result = CliRunner().invoke(group, ["question-hold", "morning"])
    assert result.exit_code == 0
    assert "should the night window start at ten?" in result.output
    empty = CliRunner().invoke(group, ["question-hold", "morning"])  # read-only: not consumed
    assert "should the night window start at ten?" in empty.output


def _rows(*questions):
    return [{"question": q, "at": 1_700_000_000.0 + i} for i, q in enumerate(questions)]


def test_letter_section_is_empty_when_nothing_was_carried(qh):
    assert qh.morning_letter_section([]) == ""


def test_letter_section_with_one_question_asks_it(qh):
    out = qh.morning_letter_section(_rows("which colour for the felt?"))
    assert "## Questions from the night" in out
    assert "I carried this while you were away." in out
    assert "1. which colour for the felt?" in out
    assert "Can wait" not in out


def test_letter_section_with_three_asks_two_and_lets_the_rest_wait(qh):
    out = qh.morning_letter_section(_rows("first?", "second?", "third?"))
    assert "1. first?" in out and "2. second?" in out
    assert "3. third?" not in out
    assert "Can wait, no need to answer these now:" in out
    assert "- third?" in out
    assert out.index("1. first?") < out.index("2. second?") < out.index("- third?")


def test_letter_section_with_two_asks_both_and_no_waiting_part(qh):
    out = qh.morning_letter_section(_rows("first?", "second?"))
    assert "1. first?" in out and "2. second?" in out
    assert "Can wait" not in out


def test_letter_section_reads_the_real_list_and_changes_nothing(qh):
    qh.MORNING.write_text(
        json.dumps({"kind": "carried", "question": "real one?", "at": time.time()}) + "\n"
    )
    before = qh.MORNING.read_text()
    assert "real one?" in qh.morning_letter_section()
    assert qh.MORNING.read_text() == before
