"""Tests for lesson regression detection and escalation.

When a lesson cycles between IMPROVING and ACTIVE, that's a regression.
After enough regressions, the lesson should be flagged for directive
promotion — structure over willpower.
"""

import json

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge.lessons import (
    REGRESSION_ESCALATION_THRESHOLD,
    auto_resolve_lessons,
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

    def test_same_session_does_not_double_count_regression(self):
        """Re-scanning the same session must not inflate regressions."""
        record_lesson("test_dedup_reg", "test lesson", "s1")
        record_lesson("test_dedup_reg", "test lesson", "s2")
        record_lesson("test_dedup_reg", "test lesson", "s3")
        mark_lesson_improving("test_dedup_reg", "clean-1")
        # First call with s4 — real regression
        record_lesson("test_dedup_reg", "test lesson", "s4")
        lessons = get_lessons(category="test_dedup_reg")
        assert lessons[0]["regressions"] == 1
        # Mark improving again, then re-trigger with SAME session s4
        mark_lesson_improving("test_dedup_reg", "clean-2")
        record_lesson("test_dedup_reg", "test lesson", "s4")  # duplicate
        lessons = get_lessons(category="test_dedup_reg")
        # Should still be 1, not 2 — s4 was already counted
        assert lessons[0]["regressions"] == 1
        assert lessons[0]["occurrences"] == 4

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


class TestAutoResolve:
    """Auto-promote improving lessons to resolved after enough clean sessions."""

    def test_no_improving_returns_empty(self):
        resolved = auto_resolve_lessons()
        assert resolved == []

    def test_improving_not_enough_sessions_stays(self):
        """Improving lesson without enough clean sessions stays improving."""
        record_lesson("test_stay_improving", "desc", "s1")
        record_lesson("test_stay_improving", "desc", "s2")
        record_lesson("test_stay_improving", "desc", "s3")
        mark_lesson_improving("test_stay_improving", "s4")

        resolved = auto_resolve_lessons()
        assert resolved == []

        lessons = get_lessons(status="improving")
        cats = [lesson["category"] for lesson in lessons]
        assert "test_stay_improving" in cats

    def test_improving_lesson_tracks_clean_sessions(self):
        """Once a lesson is 'improving', clean sessions still get tracked.

        Without this, the sessions list freezes at transition time and the
        resolution session-count gate can never be satisfied.
        """
        record_lesson("test_track_clean", "desc", "s1")
        record_lesson("test_track_clean", "desc", "s2")
        record_lesson("test_track_clean", "desc", "s3")
        mark_lesson_improving("test_track_clean", "s4")  # transitions active → improving

        lessons = get_lessons(category="test_track_clean")
        assert lessons[0]["status"] == "improving"
        initial_sessions = lessons[0]["sessions"]
        if isinstance(initial_sessions, str):
            initial_sessions = json.loads(initial_sessions)
        assert "s4" in initial_sessions

        # Now mark improving again with new clean sessions
        mark_lesson_improving("test_track_clean", "s5")
        mark_lesson_improving("test_track_clean", "s6")

        lessons = get_lessons(category="test_track_clean")
        assert lessons[0]["status"] == "improving"
        updated_sessions = lessons[0]["sessions"]
        if isinstance(updated_sessions, str):
            updated_sessions = json.loads(updated_sessions)
        assert "s5" in updated_sessions
        assert "s6" in updated_sessions
        assert len(updated_sessions) == len(initial_sessions) + 2

    def test_improving_enough_sessions_resolves(self):
        """Improving lesson with enough clean sessions gets resolved.

        Stimulus-presence gates must also be satisfied:
        - Time gate: lesson must be in 'improving' for >= LESSON_MIN_RESOLUTION_DAYS
        - Stimulus gate: clean sessions must contain category-relevant events
        """
        import json
        import time

        from divineos.core.constants import LESSON_MIN_RESOLUTION_DAYS, SECONDS_PER_DAY
        from divineos.core.knowledge import _get_connection
        from divineos.core.ledger import get_connection as get_ledger_connection

        record_lesson("test_auto_resolve", "desc", "s1")
        record_lesson("test_auto_resolve", "desc", "s2")
        record_lesson("test_auto_resolve", "desc", "s3")
        mark_lesson_improving("test_auto_resolve", "s4")

        # Add enough sessions to meet threshold.
        # With log-scaling, effective = max(5, int(log2(3)+2)) = 5,
        # so we need 5 + 5 (clean_session_threshold) = 10 total sessions.
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT sessions FROM lesson_tracking WHERE category = 'test_auto_resolve'"
            ).fetchone()
            sessions = json.loads(row[0])
            for i in range(5, 12):
                sessions.append(f"s{i}")
            conn.execute(
                "UPDATE lesson_tracking SET sessions = ? WHERE category = 'test_auto_resolve'",
                (json.dumps(sessions),),
            )
            # Backdate last_seen to satisfy the time gate
            old_enough = time.time() - (LESSON_MIN_RESOLUTION_DAYS + 1) * SECONDS_PER_DAY
            conn.execute(
                "UPDATE lesson_tracking SET last_seen = ? WHERE category = 'test_auto_resolve'",
                (old_enough,),
            )
            conn.commit()
        finally:
            conn.close()

        # Add decision journal entries with category keyword so stimulus gate passes.
        # "test_auto_resolve" has keywords ["test", "auto", "resolve"].
        ledger_conn = get_ledger_connection()
        try:
            ledger_conn.execute(
                """CREATE TABLE IF NOT EXISTS decision_journal (
                    decision_id TEXT PRIMARY KEY, created_at REAL, content TEXT,
                    reasoning TEXT DEFAULT '', alternatives TEXT DEFAULT '[]',
                    context TEXT DEFAULT '', emotional_weight INTEGER DEFAULT 1,
                    tags TEXT DEFAULT '[]', linked_knowledge_ids TEXT DEFAULT '[]',
                    session_id TEXT DEFAULT '', tension TEXT DEFAULT '',
                    almost TEXT DEFAULT '')"""
            )
            for sid in ["s5", "s6", "s7"]:
                ledger_conn.execute(
                    "INSERT INTO decision_journal (decision_id, created_at, content, session_id) "
                    "VALUES (?, ?, ?, ?)",
                    (f"dj-{sid}", time.time(), "Decided to auto resolve the test issue", sid),
                )
            ledger_conn.commit()
        finally:
            ledger_conn.close()

        resolved = auto_resolve_lessons()
        assert len(resolved) == 1
        assert resolved[0]["category"] == "test_auto_resolve"

        db_lessons = get_lessons(status="resolved")
        cats = [lesson["category"] for lesson in db_lessons]
        assert "test_auto_resolve" in cats

    def test_active_not_resolved(self):
        """Active lessons are never auto-resolved."""
        record_lesson("test_active_no_resolve", "desc", "s1")
        resolved = auto_resolve_lessons()
        assert resolved == []

    def test_time_gate_blocks_premature_resolution(self):
        """Lesson can't resolve before LESSON_MIN_RESOLUTION_DAYS even with enough sessions."""
        import json

        from divineos.core.knowledge import _get_connection

        record_lesson("test_time_gate", "desc", "s1")
        record_lesson("test_time_gate", "desc", "s2")
        record_lesson("test_time_gate", "desc", "s3")
        mark_lesson_improving("test_time_gate", "s4")

        # Add enough sessions but DON'T backdate — last_seen is ~now
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT sessions FROM lesson_tracking WHERE category = 'test_time_gate'"
            ).fetchone()
            sessions = json.loads(row[0])
            for i in range(5, 10):
                sessions.append(f"s{i}")
            conn.execute(
                "UPDATE lesson_tracking SET sessions = ? WHERE category = 'test_time_gate'",
                (json.dumps(sessions),),
            )
            conn.commit()
        finally:
            conn.close()

        # Should NOT resolve — time gate blocks it (lesson just entered improving)
        resolved = auto_resolve_lessons()
        cats = [r["category"] for r in resolved]
        assert "test_time_gate" not in cats

        # Lesson should still be improving
        lessons = get_lessons(status="improving")
        cats = [lesson["category"] for lesson in lessons]
        assert "test_time_gate" in cats

    def test_stimulus_gate_blocks_without_relevant_events(self):
        """Lesson can't resolve without stimulus-relevant events in clean sessions."""
        import json
        import time

        from divineos.core.constants import LESSON_MIN_RESOLUTION_DAYS, SECONDS_PER_DAY
        from divineos.core.knowledge import _get_connection

        record_lesson("test_stimulus_gate", "desc", "s1")
        record_lesson("test_stimulus_gate", "desc", "s2")
        record_lesson("test_stimulus_gate", "desc", "s3")
        mark_lesson_improving("test_stimulus_gate", "s4")

        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT sessions FROM lesson_tracking WHERE category = 'test_stimulus_gate'"
            ).fetchone()
            sessions = json.loads(row[0])
            for i in range(5, 10):
                sessions.append(f"s{i}")
            conn.execute(
                "UPDATE lesson_tracking SET sessions = ? WHERE category = 'test_stimulus_gate'",
                (json.dumps(sessions),),
            )
            # Backdate to pass time gate
            old_enough = time.time() - (LESSON_MIN_RESOLUTION_DAYS + 1) * SECONDS_PER_DAY
            conn.execute(
                "UPDATE lesson_tracking SET last_seen = ? WHERE category = 'test_stimulus_gate'",
                (old_enough,),
            )
            conn.commit()
        finally:
            conn.close()

        # Should NOT resolve — no events matching "stimulus" or "gate" in any session
        resolved = auto_resolve_lessons()
        cats = [r["category"] for r in resolved]
        assert "test_stimulus_gate" not in cats


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
