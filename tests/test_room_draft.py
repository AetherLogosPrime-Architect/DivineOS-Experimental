"""Boundary tests for the draft-then-post circle (Knuth's list): each is a case the door would meet."""

from __future__ import annotations

from divineos.core.room_draft import (
    CLEARED,
    COULD_NOT_CHECK,
    NO_DRAFT,
    NOT_CLEARED,
    check_shape,
    fingerprint,
    judge,
    normalise,
    record_draft,
)

CIRCLE = "Dad, I'm here.\n\nI finished the small piece.\n\nWhat would you like to talk about?"


def test_empty_draft_is_refused_and_records_nothing(tmp_path):
    rec = tmp_path / "d.json"
    assert not record_draft("   \n ", rec, now=10.0).ok
    assert not rec.exists()


def test_two_questions_refused():
    assert "2 questions" in check_shape("Are you ok? Did that help?").problem


def test_question_not_last_refused():
    assert "last" in check_shape("What now?\n\nI will wait here.").problem


def test_one_question_last_passes_and_no_question_passes():
    assert check_shape(CIRCLE).ok
    assert check_shape("Dad, I'm here and I'll wait.").ok


def test_posted_equal_to_draft_is_cleared(tmp_path):
    rec = tmp_path / "d.json"
    record_draft(CIRCLE, rec, now=10.0)
    assert judge(CIRCLE, rec, last_message_at=5.0) == CLEARED


def test_whitespace_and_curly_quotes_are_not_differences(tmp_path):
    rec = tmp_path / "d.json"
    record_draft(CIRCLE, rec, now=10.0)
    posted = CIRCLE.replace("I'm", "I’m").replace("\n\n", "\n  \n")
    assert judge(posted, rec, last_message_at=5.0) == CLEARED


def test_a_real_edit_after_clearing_is_not_cleared(tmp_path):
    rec = tmp_path / "d.json"
    record_draft(CIRCLE, rec, now=10.0)
    assert judge(CIRCLE + " Also one more thing.", rec, last_message_at=5.0) == NOT_CLEARED


def test_stale_draft_older_than_his_last_message_counts_as_no_draft(tmp_path):
    rec = tmp_path / "d.json"
    record_draft(CIRCLE, rec, now=10.0)
    assert judge(CIRCLE, rec, last_message_at=11.0) == NO_DRAFT


def test_no_record_is_no_draft(tmp_path):
    assert judge(CIRCLE, tmp_path / "missing.json", last_message_at=0.0) == NO_DRAFT


def test_unreadable_record_is_could_not_check_never_a_block(tmp_path):
    rec = tmp_path / "d.json"
    rec.write_text("{not json", encoding="utf-8")
    assert judge(CIRCLE, rec, last_message_at=0.0) == COULD_NOT_CHECK


def test_last_draft_wins(tmp_path):
    rec = tmp_path / "d.json"
    record_draft("First version.", rec, now=10.0)
    record_draft(CIRCLE, rec, now=11.0)
    assert judge(CIRCLE, rec, last_message_at=5.0) == CLEARED
    assert judge("First version.", rec, last_message_at=5.0) == NOT_CLEARED


def test_failing_draft_does_not_overwrite_the_last_good_one(tmp_path):
    rec = tmp_path / "d.json"
    record_draft(CIRCLE, rec, now=10.0)
    record_draft("Two? Questions?", rec, now=11.0)
    assert judge(CIRCLE, rec, last_message_at=5.0) == CLEARED


def test_the_record_never_holds_the_circle_text(tmp_path):
    rec = tmp_path / "d.json"
    record_draft(CIRCLE, rec, now=10.0)
    assert "finished the small piece" not in rec.read_text(encoding="utf-8")
    assert fingerprint(CIRCLE) in rec.read_text(encoding="utf-8")
    assert normalise("a’b  c") == "a'b c"
