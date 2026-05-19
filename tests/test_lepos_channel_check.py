"""Tests for lepos_channel_check — the YES/AND lepos-channel gate.

Per prereg-157ed56a5da2 the gate runs as a 30-turn empirical trial.
These tests cover the substrate contract (selection, persistence,
evaluation), not the foundational question wording — that's expected
to iterate during the trial.
"""

from __future__ import annotations


import pytest

from divineos.core import lepos_channel_check as lcc


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Point divineos_home at a tmp dir so tests don't write the user's
    real lepos_channel_log.db."""
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    # Reset cached current-turn-file path
    monkeypatch.setattr(lcc, "_CURRENT_TURN_FILE", tmp_path / "lepos_current_turn_questions.json")
    yield


def test_selection_has_required_content_aware_slots():
    qs = lcc.select_questions_for_turn(seed=1)
    assert len(qs) == lcc._QUESTIONS_PER_TURN
    ca_count = sum(1 for q in qs if q.content_aware)
    assert ca_count >= lcc._MIN_CONTENT_AWARE


def test_selection_is_deterministic_with_seed():
    a = lcc.select_questions_for_turn(seed=42)
    b = lcc.select_questions_for_turn(seed=42)
    assert tuple(q.id for q in a) == tuple(q.id for q in b)


def test_selection_varies_across_seeds():
    # Across a reasonable seed range, at least two sets differ —
    # Beer variety requirement.
    sets = {tuple(q.id for q in lcc.select_questions_for_turn(seed=s)) for s in range(20)}
    assert len(sets) >= 2


def test_format_block_persists_current_turn():
    qs = lcc.select_questions_for_turn(seed=7)
    lcc.format_check_block(qs)
    back = lcc.load_current_turn_questions()
    assert tuple(q.id for q in back) == tuple(q.id for q in qs)


def test_evaluate_absent_when_no_question_ids_or_prompts_in_response():
    qs = lcc.select_questions_for_turn(seed=3)
    ev = lcc.evaluate_response("Just a normal reply with no check answers.", qs)
    assert ev.status == "absent"


def test_evaluate_running_when_ids_present_with_substance():
    qs = lcc.select_questions_for_turn(seed=11)
    # Construct a response that contains every question id plus
    # substantive text per answer.
    body = "lepos check:\n" + "\n".join(
        f"- {q.id}: I am answering this question specifically by pointing "
        f"at where in this very reply the evidence lives, namely the "
        f"sentence that follows."
        for q in qs
    )
    ev = lcc.evaluate_response(body, qs)
    assert ev.status == "running"
    assert set(ev.answered_question_ids) == {q.id for q in qs}


def test_evaluate_thin_on_consecutive_one_word_affirmations():
    qs = lcc.select_questions_for_turn(seed=5)
    # Include the question ids so it isn't classed "absent", but with
    # bare yes/yes/yes answers.
    body = (
        f"{qs[0].id}\nyes\n{qs[1].id}\nyes\n{qs[2].id}\nyes\n{qs[3].id}\nyes\n"
        + "More substantive padding to push length past the threshold. " * 20
    )
    ev = lcc.evaluate_response(body, qs)
    assert ev.status == "thin"


def test_log_turn_persists_to_db_and_is_readable():
    qs = lcc.select_questions_for_turn(seed=9)
    ev = lcc.ChannelEvaluation(
        status="running", answered_question_ids=tuple(q.id for q in qs), note="ok"
    )
    rid = lcc.log_turn(qs, "some response excerpt here", ev)
    assert rid > 0
    rows = lcc.recent_turns(limit=10)
    assert rows
    assert rows[0]["status"] == "running"
    assert rows[0]["note"] == "ok"


def test_briefing_summary_empty_when_no_logs():
    assert lcc.briefing_summary() == ""


def test_briefing_summary_counts_after_logs():
    qs = lcc.select_questions_for_turn(seed=2)
    for status in ("running", "running", "thin", "absent"):
        ev = lcc.ChannelEvaluation(
            status=status, answered_question_ids=tuple(q.id for q in qs), note=""
        )
        lcc.log_turn(qs, "x", ev)
    s = lcc.briefing_summary(limit=10)
    assert "running: 2" in s
    assert "thin: 1" in s
    assert "absent: 1" in s


def test_module_has_guardrail_marker():
    """Aletheia Finding 48 class-fix discipline: any load-bearing
    enforcement module must declare itself for multi-party review."""
    assert getattr(lcc, "__guardrail_required__", False) is True
