"""Tests for external validation — user feedback on self-grades."""

import sqlite3

import pytest

from divineos.core.external_validation import (
    format_origin_summary,
    format_validation_summary,
    get_knowledge_origin_ratio,
    get_validation_accuracy,
    init_validation_table,
    record_self_grade,
    record_user_feedback,
)


@pytest.fixture(autouse=True)
def _clean_validation_table():
    """Ensure clean validation table for each test."""
    init_validation_table()
    from divineos.core.knowledge._base import _get_connection

    conn = _get_connection()
    try:
        conn.execute("DELETE FROM session_validation")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()
    yield


class TestRecordSelfGrade:
    def test_returns_validation_id(self):
        vid = record_self_grade("sess-1", "B", 0.75)
        assert vid.startswith("val-")

    def test_stores_grade(self):
        record_self_grade("sess-1", "A", 0.92)
        from divineos.core.knowledge._base import _get_connection

        conn = _get_connection()
        row = conn.execute(
            "SELECT self_grade, self_score FROM session_validation WHERE session_id = ?",
            ("sess-1",),
        ).fetchone()
        conn.close()
        assert row[0] == "A"
        assert row[1] == pytest.approx(0.92)


class TestRecordUserFeedback:
    def test_agree_matches(self):
        record_self_grade("sess-1", "B", 0.75)
        ok = record_user_feedback("sess-1", "agree")
        assert ok is True
        acc = get_validation_accuracy()
        assert acc["matches"] == 1

    def test_disagree_no_match(self):
        record_self_grade("sess-1", "A", 0.9)
        record_user_feedback("sess-1", "disagree")
        acc = get_validation_accuracy()
        assert acc["matches"] == 0
        assert acc["total"] == 1

    def test_same_letter_matches(self):
        record_self_grade("sess-1", "B", 0.75)
        record_user_feedback("sess-1", "B")
        acc = get_validation_accuracy()
        assert acc["matches"] == 1

    def test_different_letter_no_match(self):
        record_self_grade("sess-1", "A", 0.9)
        record_user_feedback("sess-1", "D")
        acc = get_validation_accuracy()
        assert acc["matches"] == 0

    def test_no_self_grade_returns_false(self):
        ok = record_user_feedback("nonexistent", "B")
        assert ok is False

    def test_yes_shorthand_matches(self):
        record_self_grade("sess-1", "C", 0.5)
        record_user_feedback("sess-1", "y")
        acc = get_validation_accuracy()
        assert acc["matches"] == 1


class TestValidationAccuracy:
    def test_empty_returns_zero(self):
        acc = get_validation_accuracy()
        assert acc["total"] == 0
        assert acc["accuracy"] == 0.0

    def test_perfect_accuracy(self):
        for i in range(5):
            record_self_grade(f"sess-{i}", "B", 0.75)
            record_user_feedback(f"sess-{i}", "agree")
        acc = get_validation_accuracy()
        assert acc["accuracy"] == 1.0

    def test_mixed_accuracy(self):
        record_self_grade("sess-1", "A", 0.9)
        record_user_feedback("sess-1", "agree")
        record_self_grade("sess-2", "A", 0.9)
        record_user_feedback("sess-2", "D")
        acc = get_validation_accuracy()
        assert acc["accuracy"] == 0.5
        assert len(acc["recent_mismatches"]) == 1

    def test_recent_mismatches_capped(self):
        for i in range(10):
            record_self_grade(f"sess-{i}", "A", 0.9)
            record_user_feedback(f"sess-{i}", "F")
        acc = get_validation_accuracy()
        assert len(acc["recent_mismatches"]) <= 5


class TestKnowledgeOriginRatio:
    def test_returns_dict(self):
        ratio = get_knowledge_origin_ratio()
        assert "total" in ratio
        assert "inherited" in ratio
        assert "learned" in ratio
        assert "learned_ratio" in ratio

    def test_ratio_between_zero_and_one(self):
        ratio = get_knowledge_origin_ratio()
        assert 0.0 <= ratio["learned_ratio"] <= 1.0


class TestFormatSummaries:
    def test_origin_summary_is_string(self):
        s = format_origin_summary()
        assert isinstance(s, str)

    def test_validation_summary_no_feedback(self):
        s = format_validation_summary()
        assert "No user feedback" in s

    def test_validation_summary_with_feedback(self):
        record_self_grade("sess-1", "B", 0.75)
        record_user_feedback("sess-1", "agree")
        s = format_validation_summary()
        assert "100%" in s
