"""Tests for lesson regression detection and escalation.

When a lesson cycles between IMPROVING and ACTIVE, that's a regression.
After enough regressions, the lesson should be flagged for directive
promotion — structure over willpower.
"""

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge.lessons import (
    REGRESSION_ESCALATION_THRESHOLD,
    get_escalation_candidates,
    get_lesson_summary,
    get_lessons,
    mark_lesson_improving,
    record_lesson,
)


@pytest.fixture(autouse=True)
def _init_knowledge():
    """Ensure knowledge tables (including lesson_tracking) exist."""
    init_knowledge_table()


class TestRegressionDetection:
    """Detect when an IMPROVING lesson reverts to ACTIVE."""

    def test_new_lesson_has_zero_regressions(self):
        record_lesson("test_new_zero", "test lesson", "session-1")
        lessons = get_lessons(category="test_new_zero")
        assert lessons[0].get("regressions", 0) == 0

    def test_recurring_active_lesson_no_regression(self):
        """Recurring while ACTIVE is not a regression — it was never improving."""
        record_lesson("test_active_recur", "test lesson", "session-1")
        record_lesson("test_active_recur", "test lesson", "session-2")
        record_lesson("test_active_recur", "test lesson", "session-3")
        lessons = get_lessons(category="test_active_recur")
        assert lessons[0]["regressions"] == 0
        assert lessons[0]["occurrences"] == 3

    def test_improving_then_recurring_is_regression(self):
        """IMPROVING → recurrence = regression detected."""
        record_lesson("test_regress", "test lesson", "session-1")
        record_lesson("test_regress", "test lesson", "session-2")
        record_lesson("test_regress", "test lesson", "session-3")
        # Mark as improving
        mark_lesson_improving("test_regress", "clean-session")
        # Verify it's improving
        lessons = get_lessons(category="test_regress")
        assert lessons[0]["status"] == "improving"
        # Now recur — this should be a regression
        record_lesson("test_regress", "test lesson", "session-4")
        lessons = get_lessons(category="test_regress")
        assert lessons[0]["status"] == "active"
        assert lessons[0]["regressions"] == 1

    def test_multiple_regressions_accumulate(self):
        """Each IMPROVING → ACTIVE cycle increments the regression count."""
        record_lesson("test_multi_regress", "test lesson", "s1")
        record_lesson("test_multi_regress", "test lesson", "s2")
        record_lesson("test_multi_regress", "test lesson", "s3")

        for i in range(3):
            mark_lesson_improving("test_multi_regress", f"clean-{i}")
            record_lesson("test_multi_regress", "test lesson", f"regress-{i}")

        lessons = get_lessons(category="test_multi_regress")
        assert lessons[0]["regressions"] == 3

    def test_regression_threshold_defined(self):
        assert REGRESSION_ESCALATION_THRESHOLD == 3


class TestEscalationCandidates:
    """Lessons with enough regressions become escalation candidates."""

    def test_no_candidates_when_no_regressions(self):
        record_lesson("test_no_escalate", "test lesson", "s1")
        candidates = get_escalation_candidates()
        # Should not include lessons with 0 regressions
        cats = [c["category"] for c in candidates]
        assert "test_no_escalate" not in cats

    def test_candidate_after_threshold_regressions(self):
        record_lesson("test_escalate_me", "keeps failing", "s1")
        record_lesson("test_escalate_me", "keeps failing", "s2")
        record_lesson("test_escalate_me", "keeps failing", "s3")

        for i in range(REGRESSION_ESCALATION_THRESHOLD):
            mark_lesson_improving("test_escalate_me", f"clean-{i}")
            record_lesson("test_escalate_me", "keeps failing", f"regress-{i}")

        candidates = get_escalation_candidates()
        cats = [c["category"] for c in candidates]
        assert "test_escalate_me" in cats


class TestLessonSummaryWithRegressions:
    """Summary output includes regression info."""

    def test_summary_shows_regression_count(self):
        record_lesson("test_summary_regress", "test lesson for summary", "s1")
        record_lesson("test_summary_regress", "test lesson for summary", "s2")
        record_lesson("test_summary_regress", "test lesson for summary", "s3")
        mark_lesson_improving("test_summary_regress", "clean-1")
        record_lesson("test_summary_regress", "test lesson for summary", "s4")

        summary = get_lesson_summary()
        assert "regressed" in summary

    def test_summary_shows_escalate_flag(self):
        record_lesson("test_summary_escalate", "keeps recurring", "s1")
        record_lesson("test_summary_escalate", "keeps recurring", "s2")
        record_lesson("test_summary_escalate", "keeps recurring", "s3")

        for i in range(REGRESSION_ESCALATION_THRESHOLD):
            mark_lesson_improving("test_summary_escalate", f"clean-{i}")
            record_lesson("test_summary_escalate", "keeps recurring", f"r-{i}")

        summary = get_lesson_summary()
        assert "ESCALATE" in summary
