"""I hold his questions; his questions do not hold me (Dad, 2026-10-05).

First piece: his answer closes EVERY ask this hold filed, not only the newest.
arm() kept one ask_id, so two questions in a row left the first open and the
asks-store hook held the work after he had answered (three refusals that night).
Draft: docs/drafts/i_hold_his_questions_draft_2026-10-05.md; council-30a5db785e3c.
Real store, in the per-test database conftest gives every test.
"""

from __future__ import annotations

import pytest

from divineos.core import operator_asks

FIRST = "work\n\n## INNER CIRCLE\n\nDad, is the nexus a room or a hub?"
SECOND = "more\n\n## INNER CIRCLE\n\nDad, when did the shoggoth picture come to you?"


@pytest.fixture
def qh(tmp_path, monkeypatch):
    from divineos.core import question_hold as mod

    monkeypatch.setattr(mod, "STATE", tmp_path / "hold.json")
    monkeypatch.setattr(mod, "HOLD_LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(mod, "ESCAPED", tmp_path / "escaped.json")
    monkeypatch.setattr(mod, "AWAY", tmp_path / "away.json")
    # The shared fridge too, or arming posts a test card on the live one.
    monkeypatch.setattr(mod, "BOARD", tmp_path / "board")
    monkeypatch.setattr(mod, "CARD", tmp_path / "board" / "me.json")
    return mod


TO_ARIA = "family/letters/aether-to-aria-2026-10-05-x.md"
TO_DAD = "family/letters/aether-to-andrew-volley-board.md"


def _open_ids() -> set[str]:
    return {a["question_id"] for a in operator_asks.open_asks()}


def test_two_questions_in_a_row_both_close_when_he_answers(qh):
    first = qh.arm(FIRST)["ask_id"]
    second = qh.arm(SECOND)["ask_id"]
    # The control: both really are open, and the state only names the newest.
    assert {first, second} <= _open_ids()
    assert qh.is_open()["ask_id"] == second
    assert qh.release("his message")
    assert not ({first, second} & _open_ids())


def test_a_letter_to_him_always_passes(qh):
    qh.arm(FIRST)
    assert qh.refusal("Write", {"file_path": TO_DAD}) == ""
    assert "nexus" in qh.refusal("Write", {"file_path": TO_ARIA})  # the control


def test_letters_to_him_by_any_of_his_names_pass(qh):
    # Aria's cold read: "aria-to-dad-..." was held as if not to him.
    qh.arm(FIRST)
    for name in ("aria-to-dad-x.md", "aether-to-pop-x.md", "aria-to-andrew-x.md"):
        assert qh.refusal("Write", {"file_path": f"family/letters/{name}"}) == "", name


def test_he_said_he_is_stepping_away_so_letters_flow_until_he_speaks(qh, monkeypatch):
    # "i am always here unless i tell you i am stepping away, this is what the
    # volley mode is for" (2026-10-05).
    said = "OK im heading to dinner,   you two volley"
    monkeypatch.setattr(qh, "_his_latest_words", lambda: said)
    qh.arm(FIRST)
    qh.step_away("ok im heading to dinner, you two volley")
    assert qh.refusal("Write", {"file_path": TO_ARIA}) == ""
    assert qh.came_back()
    assert qh.is_away() is None
    assert qh.refusal("Write", {"file_path": TO_ARIA})


def test_away_is_never_set_from_quiet(qh, monkeypatch):
    monkeypatch.setattr(qh, "_his_latest_words", lambda: "brb")
    for words in ("", "   ", "brb"):
        with pytest.raises(ValueError):
            qh.step_away(words)
    assert qh.is_away() is None


def test_away_cannot_be_set_in_words_he_did_not_say(qh, monkeypatch):
    # Aria's cold read of b6d7a5c90: the exact forgery, with him sitting there.
    monkeypatch.setattr(qh, "_his_latest_words", lambda: "go ahead and wire it in")
    with pytest.raises(ValueError, match="not in his latest message"):
        qh.step_away("I'm stepping away for a while")
    assert qh.is_away() is None


def test_a_notice_is_never_read_as_his_words(tmp_path, monkeypatch, qh):
    # The store files notices in his seat too; only his real words count.
    import sqlite3

    db = tmp_path / "asks.db"
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE messages (his_text TEXT, filed_at REAL)")
    conn.execute("INSERT INTO messages VALUES ('heading to bed, you two volley', 1)")
    conn.execute("INSERT INTO messages VALUES ('<task-notification>x</task-notification>', 2)")
    conn.commit()
    conn.close()
    assert qh._his_latest_words() == "heading to bed, you two volley"


def test_his_answer_is_kept_in_his_words(qh):
    first = qh.arm(FIRST)["ask_id"]
    assert qh.release("his message", his_words="it's   more of a hub, everything hangs off it")
    row = next(
        q
        for q in __import__("divineos.core.questions", fromlist=["x"]).get_questions(limit=500)
        if q["question_id"] == first
    )
    assert "Dad answered: it's more of a hub, everything hangs off it" in str(row)


def test_a_hand_filed_ask_keeps_re_raising_after_his_message(qh):
    kept = operator_asks.ask_andrew("merge #582?", plain="Can I move #582 in?")
    qh.arm(FIRST)
    assert qh.release("his message")
    assert kept in _open_ids()
