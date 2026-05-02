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
    STATUS_ACTIVE,
    STATUS_DORMANT,
    STATUS_RESOLVED,
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

        # Under the 2026-04-16 rebuild, clean sessions alone don't reach
        # RESOLVED — that would be granting learning from absence of
        # complaint (the Kahneman failure mode). With regressions == 0
        # and enough wall-clock silence, the honest transition is DORMANT
        # ("quiet, not proven"). RESOLVED now requires positive-
        # counterfactual evidence; see test_improving_resolves_with_positive_evidence.
        transitioned = auto_resolve_lessons()
        assert len(transitioned) == 1
        assert transitioned[0]["category"] == "test_auto_resolve"
        assert transitioned[0]["status"] == STATUS_DORMANT

        db_lessons = get_lessons(status=STATUS_DORMANT)
        cats = [lesson["category"] for lesson in db_lessons]
        assert "test_auto_resolve" in cats

        # And it explicitly did NOT reach resolved.
        resolved_cats = [lesson["category"] for lesson in get_lessons(status=STATUS_RESOLVED)]
        assert "test_auto_resolve" not in resolved_cats

    def test_improving_resolves_with_positive_evidence(self):
        """With LESSON_MIN_POSITIVE_EVIDENCE positive-counterfactual
        sessions plus the time and stimulus gates, improving → resolved.
        This is the Kahneman-compliant happy path.
        """
        import time

        from divineos.core.constants import LESSON_MIN_RESOLUTION_DAYS, SECONDS_PER_DAY
        from divineos.core.knowledge import _get_connection
        from divineos.core.ledger import get_connection as get_ledger_connection

        record_lesson("test_positive_evidence", "desc", "s1")
        record_lesson("test_positive_evidence", "desc", "s2")
        record_lesson("test_positive_evidence", "desc", "s3")
        # Positive-evidence session transitions active → improving.
        mark_lesson_improving(
            "test_positive_evidence",
            "s4",
            evidence="agent demonstrated corrected behavior in s4",
        )
        # Second positive-evidence session — meets LESSON_MIN_POSITIVE_EVIDENCE.
        mark_lesson_improving(
            "test_positive_evidence",
            "s5",
            evidence="agent demonstrated corrected behavior in s5",
        )

        # Pad the session count and backdate last_seen to satisfy the
        # remaining gates, same as the previous test.
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT sessions FROM lesson_tracking WHERE category = 'test_positive_evidence'"
            ).fetchone()
            sessions = json.loads(row[0])
            for i in range(6, 12):
                sessions.append(f"s{i}")
            conn.execute(
                "UPDATE lesson_tracking SET sessions = ? WHERE category = 'test_positive_evidence'",
                (json.dumps(sessions),),
            )
            old_enough = time.time() - (LESSON_MIN_RESOLUTION_DAYS + 1) * SECONDS_PER_DAY
            conn.execute(
                "UPDATE lesson_tracking SET last_seen = ? WHERE category = 'test_positive_evidence'",
                (old_enough,),
            )
            conn.commit()
        finally:
            conn.close()

        # Stimulus gate: decision journal entries mentioning the category.
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
            for sid in ["s6", "s7", "s8"]:
                ledger_conn.execute(
                    "INSERT INTO decision_journal (decision_id, created_at, content, session_id) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        f"dj-{sid}",
                        time.time(),
                        "Decided to handle test positive evidence case",
                        sid,
                    ),
                )
            ledger_conn.commit()
        finally:
            ledger_conn.close()

        transitioned = auto_resolve_lessons()
        assert len(transitioned) == 1
        assert transitioned[0]["category"] == "test_positive_evidence"
        assert transitioned[0]["status"] == STATUS_RESOLVED

        resolved_cats = [lesson["category"] for lesson in get_lessons(status=STATUS_RESOLVED)]
        assert "test_positive_evidence" in resolved_cats

    def test_dormant_lesson_reverts_to_active_on_regression(self):
        """DORMANT → ACTIVE on new occurrence, with regression counter
        bumped (Popper: dormant is revertible, not a terminal state)."""
        import time

        from divineos.core.constants import LESSON_ABSENCE_DAYS, SECONDS_PER_DAY
        from divineos.core.knowledge import _get_connection

        # Build a dormant lesson: occurrences 3, no positive evidence,
        # enough wall-clock silence, zero regressions.
        record_lesson("test_dormant_revert", "desc", "s1")
        record_lesson("test_dormant_revert", "desc", "s2")
        record_lesson("test_dormant_revert", "desc", "s3")
        mark_lesson_improving("test_dormant_revert", "s4")  # absence-only

        conn = _get_connection()
        try:
            # Pad sessions + backdate last_seen.
            row = conn.execute(
                "SELECT sessions FROM lesson_tracking WHERE category = 'test_dormant_revert'"
            ).fetchone()
            sessions = json.loads(row[0])
            for i in range(5, 12):
                sessions.append(f"s{i}")
            old_enough = time.time() - (LESSON_ABSENCE_DAYS + 1) * SECONDS_PER_DAY
            conn.execute(
                "UPDATE lesson_tracking SET sessions = ?, last_seen = ? "
                "WHERE category = 'test_dormant_revert'",
                (json.dumps(sessions), old_enough),
            )
            conn.commit()
        finally:
            conn.close()

        transitioned = auto_resolve_lessons()
        assert len(transitioned) == 1
        assert transitioned[0]["status"] == STATUS_DORMANT

        # Mistake recurs — must revert to ACTIVE and bump regressions.
        record_lesson("test_dormant_revert", "desc", "s-recur")
        after = get_lessons(category="test_dormant_revert")[0]
        assert after["status"] == STATUS_ACTIVE
        assert after.get("regressions", 0) >= 1

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
            # Backdate to pass time gate. Set regressions=1 so absence_mode
            # does NOT apply — this test isolates the stimulus gate, so we
            # need to keep that gate active.
            old_enough = time.time() - (LESSON_MIN_RESOLUTION_DAYS + 1) * SECONDS_PER_DAY
            conn.execute(
                "UPDATE lesson_tracking SET last_seen = ?, regressions = 1 "
                "WHERE category = 'test_stimulus_gate'",
                (old_enough,),
            )
            conn.commit()
        finally:
            conn.close()

        # Should NOT resolve — no events matching "stimulus" or "gate" in any session
        resolved = auto_resolve_lessons()
        cats = [r["category"] for r in resolved]
        assert "test_stimulus_gate" not in cats

    def test_absence_without_evidence_transitions_to_dormant(self):
        """A long-quiet lesson with zero regressions and no positive
        evidence transitions to DORMANT — not RESOLVED.

        This was ``test_absence_mode_resolves_with_few_sessions`` under
        the pre-2026-04-16 rule that auto-resolved lessons via
        wall-clock quiet alone. Popper flagged that as an ad-hoc rescue;
        the honest transition is now DORMANT ("quiet, not proven"),
        revertible on recurrence. RESOLVED requires positive-
        counterfactual evidence — see
        test_improving_resolves_with_positive_evidence.
        """
        import json
        import time

        from divineos.core.constants import LESSON_ABSENCE_DAYS, SECONDS_PER_DAY
        from divineos.core.knowledge import _get_connection

        # Lesson with 7 occurrences across only 5 sessions (mimics real data:
        # shallow_output category was stuck like this for 21 days).
        for i in range(1, 6):
            record_lesson("test_absence_mode", "low-frequency mistake", f"s{i}")
        for i in range(6, 8):
            # Add extra occurrences in same sessions to inflate count
            record_lesson("test_absence_mode", "low-frequency mistake", f"s{(i % 5) + 1}")
        mark_lesson_improving("test_absence_mode", "s5")

        conn = _get_connection()
        try:
            # Backdate to satisfy absence-mode: zero regressions, > LESSON_ABSENCE_DAYS quiet
            old_enough = time.time() - (LESSON_ABSENCE_DAYS + 1) * SECONDS_PER_DAY
            conn.execute(
                "UPDATE lesson_tracking SET last_seen = ?, regressions = 0 "
                "WHERE category = 'test_absence_mode'",
                (old_enough,),
            )
            conn.commit()

            # Verify session count is BELOW the old session-floor (effective + 5)
            row = conn.execute(
                "SELECT sessions FROM lesson_tracking WHERE category = 'test_absence_mode'"
            ).fetchone()
            sessions = json.loads(row[0])
            assert len(sessions) < 10, "test setup: must be below old session threshold"
        finally:
            conn.close()

        transitioned = auto_resolve_lessons()
        by_cat = {r["category"]: r for r in transitioned}
        assert "test_absence_mode" in by_cat, (
            f"absence-mode should transition low-session quiet lessons; got {list(by_cat)}"
        )
        assert by_cat["test_absence_mode"]["status"] == STATUS_DORMANT, (
            "absence-only lessons must transition to DORMANT, not RESOLVED — "
            "the honest label for 'quiet but unproven'"
        )
        # And must NOT be in the resolved bucket.
        resolved_cats = [lesson["category"] for lesson in get_lessons(status=STATUS_RESOLVED)]
        assert "test_absence_mode" not in resolved_cats

    def test_absence_mode_does_not_apply_with_regressions(self):
        """A lesson that has regressed cannot use absence-mode — it must
        accumulate the full session count and pass the stimulus gate."""
        import time

        from divineos.core.constants import LESSON_ABSENCE_DAYS, SECONDS_PER_DAY
        from divineos.core.knowledge import _get_connection

        for i in range(1, 6):
            record_lesson("test_absence_with_regress", "mistake", f"s{i}")
        mark_lesson_improving("test_absence_with_regress", "s5")

        conn = _get_connection()
        try:
            # Long quiet but WITH regressions — absence-mode disabled
            old_enough = time.time() - (LESSON_ABSENCE_DAYS + 1) * SECONDS_PER_DAY
            conn.execute(
                "UPDATE lesson_tracking SET last_seen = ?, regressions = 2 "
                "WHERE category = 'test_absence_with_regress'",
                (old_enough,),
            )
            conn.commit()
        finally:
            conn.close()

        resolved = auto_resolve_lessons()
        cats = [r["category"] for r in resolved]
        assert "test_absence_with_regress" not in cats, (
            "lesson with regressions must not auto-resolve via absence-mode"
        )


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


class TestResolvedWithHistory:
    """Regressed-lesson exit via RESOLVED_WITH_HISTORY (prereg-63e87e548a04).

    Closes the terminal-state bug Grok flagged in find-f50532457f76: a
    regressed lesson could reach neither DORMANT (requires
    regressions == 0) nor RESOLVED (previously no regression guard but
    now explicit — regressed lessons cannot silently take the clean
    RESOLVED label). These tests lock:

    * Regressed lesson with positive evidence + cooldown reaches
      RESOLVED_WITH_HISTORY (the scar stays visible).
    * Regressed lesson with positive evidence but RECENT regression
      does NOT transition — the cooldown gate holds.
    * Non-regressed lesson with identical evidence reaches RESOLVED
      (not RESOLVED_WITH_HISTORY) — the new state is scoped to
      lessons that actually regressed.
    * Regressed lesson without positive evidence stays IMPROVING —
      the exit still requires evidence, just not zero regressions.
    """

    def _build_regressed_lesson(self, category: str, n_regressions: int = 1) -> None:
        """Create a category, escalate to active, then regress N times."""
        # Establish active status with 3 occurrences.
        record_lesson(category, "test regression base", "r-s1")
        record_lesson(category, "test regression base", "r-s2")
        record_lesson(category, "test regression base", "r-s3")
        # Transition to improving, then regress repeatedly.
        for i in range(n_regressions):
            mark_lesson_improving(category, f"{category}-clean-{i}")
            record_lesson(category, "regression event", f"{category}-r-{i}")

    def _prepare_gates(self, category: str, days_ago: float, extra_sessions: int = 8) -> None:
        """Pad sessions + backdate last_seen + add ledger stimulus."""
        import json as _json
        import time as _time

        from divineos.core.constants import SECONDS_PER_DAY
        from divineos.core.knowledge import _get_connection
        from divineos.core.ledger import get_connection as get_ledger_connection

        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT sessions FROM lesson_tracking WHERE category = ?",
                (category,),
            ).fetchone()
            sessions = _json.loads(row[0])
            for i in range(extra_sessions):
                sessions.append(f"{category}-pad-{i}")
            old_enough = _time.time() - days_ago * SECONDS_PER_DAY
            conn.execute(
                "UPDATE lesson_tracking SET sessions = ?, last_seen = ? WHERE category = ?",
                (_json.dumps(sessions), old_enough, category),
            )
            conn.commit()
        finally:
            conn.close()

        ledger_conn = get_ledger_connection()
        try:
            # Schema must be a strict subset of production per
            # test_schema_sync. Production decision_journal does not carry
            # `actor` or `stakes` — keep this helper aligned with
            # src/divineos/core/decision_journal.py::init_decision_journal.
            ledger_conn.execute(
                """CREATE TABLE IF NOT EXISTS decision_journal (
                    decision_id TEXT PRIMARY KEY, created_at REAL NOT NULL,
                    content TEXT NOT NULL, session_id TEXT DEFAULT '',
                    reasoning TEXT DEFAULT '',
                    alternatives TEXT DEFAULT '[]',
                    context TEXT DEFAULT '', emotional_weight INTEGER DEFAULT 1,
                    tags TEXT DEFAULT '[]', linked_knowledge_ids TEXT DEFAULT '[]',
                    tension TEXT DEFAULT '', almost TEXT DEFAULT '')"""
            )
            # Stimulus session IDs MUST match session IDs in the lesson's
            # sessions list, because _count_stimulus_sessions iterates the
            # sessions list and checks the ledger for matching session_ids.
            # Use the padded IDs we just appended above.
            # Content must contain keywords as STANDALONE words — word
            # boundary regex treats underscores as word characters, so
            # keywords embedded in "category_name" don't match. Split
            # the category and use its words in the content directly.
            keywords_text = " ".join(w for w in category.replace("_", " ").split() if len(w) >= 4)
            for sid_num in range(min(3, extra_sessions)):
                sid = f"{category}-pad-{sid_num}"
                ledger_conn.execute(
                    "INSERT INTO decision_journal (decision_id, created_at, content, session_id) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        f"dj-{sid}",
                        _time.time(),
                        f"Decided to handle a {keywords_text} case correctly this time",
                        sid,
                    ),
                )
            ledger_conn.commit()
        finally:
            ledger_conn.close()

    def test_regressed_lesson_with_evidence_reaches_resolved_with_history(self):
        """The core transition: regression + evidence + cooldown → exit."""
        from divineos.core.constants import LESSON_MIN_RESOLUTION_DAYS
        from divineos.core.knowledge.lessons import (
            LESSON_REGRESSION_COOLDOWN_DAYS,
            STATUS_RESOLVED_WITH_HISTORY,
        )

        cat = "test_rwh_happy_path"
        self._build_regressed_lesson(cat, n_regressions=1)

        # Give it positive evidence AFTER the regression.
        mark_lesson_improving(cat, f"{cat}-pos-1", evidence="corrected behavior observed")
        mark_lesson_improving(cat, f"{cat}-pos-2", evidence="corrected behavior observed again")

        # Backdate far enough for both LESSON_MIN_RESOLUTION_DAYS AND
        # LESSON_REGRESSION_COOLDOWN_DAYS to be satisfied.
        days_ago = max(LESSON_MIN_RESOLUTION_DAYS, LESSON_REGRESSION_COOLDOWN_DAYS) + 1
        self._prepare_gates(cat, days_ago=days_ago)

        transitioned = auto_resolve_lessons()
        assert any(
            lesson["category"] == cat and lesson["status"] == STATUS_RESOLVED_WITH_HISTORY
            for lesson in transitioned
        ), f"regressed lesson did not reach RESOLVED_WITH_HISTORY; got {transitioned}"

        # Regression count must be preserved (scar stays visible).
        lessons = get_lessons(category=cat)
        assert lessons[0]["regressions"] >= 1, "regression count must persist through transition"
        assert lessons[0]["status"] == STATUS_RESOLVED_WITH_HISTORY

    def test_recent_regression_blocks_resolved_with_history(self):
        """Cooldown gate: a lesson that regressed recently cannot exit.

        This is the falsifier from the pre-reg — the new transition
        must not fire while a regression is recent."""
        from divineos.core.constants import LESSON_MIN_RESOLUTION_DAYS
        from divineos.core.knowledge.lessons import (
            LESSON_REGRESSION_COOLDOWN_DAYS,
            STATUS_IMPROVING,
            STATUS_RESOLVED_WITH_HISTORY,
        )

        cat = "test_rwh_recent_regression"
        self._build_regressed_lesson(cat, n_regressions=1)
        mark_lesson_improving(cat, f"{cat}-pos-1", evidence="obs")
        mark_lesson_improving(cat, f"{cat}-pos-2", evidence="obs")

        # Backdate past LESSON_MIN_RESOLUTION_DAYS but NOT past the
        # regression cooldown. If cooldown < resolution_days, flip.
        # Pick a value strictly less than cooldown; if that is also
        # less than resolution_days, the resolution gate blocks
        # (correct — the lesson should not resolve either way).
        days_ago = max(1.0, LESSON_REGRESSION_COOLDOWN_DAYS - 5)
        assert days_ago < LESSON_REGRESSION_COOLDOWN_DAYS, (
            "test setup requires cooldown to not yet elapse"
        )
        # Resolution days check: if days_ago < LESSON_MIN_RESOLUTION_DAYS
        # too, both gates block. That is the "stays improving" assertion
        # we want either way.
        self._prepare_gates(cat, days_ago=days_ago)

        transitioned = auto_resolve_lessons()
        transitioned_cats = [lesson["category"] for lesson in transitioned]
        assert cat not in transitioned_cats, (
            "regressed lesson transitioned despite recent regression — cooldown gate failed"
        )

        lessons = get_lessons(category=cat)
        assert lessons[0]["status"] == STATUS_IMPROVING
        # Explicit check: did NOT reach RESOLVED_WITH_HISTORY.
        assert lessons[0]["status"] != STATUS_RESOLVED_WITH_HISTORY
        # Unused import guard — if LESSON_MIN_RESOLUTION_DAYS is removed
        # from the import we want a noisy failure here, not a silent
        # change to the gate semantics.
        assert LESSON_MIN_RESOLUTION_DAYS > 0

    def test_non_regressed_lesson_still_reaches_plain_resolved(self):
        """Negative control: a lesson that never regressed takes the
        clean RESOLVED path. RESOLVED_WITH_HISTORY is for lessons with
        actual history, not cosmetic scar tissue."""
        from divineos.core.constants import LESSON_MIN_RESOLUTION_DAYS
        from divineos.core.knowledge.lessons import STATUS_RESOLVED_WITH_HISTORY

        cat = "test_clean_resolved_control"
        record_lesson(cat, "test clean", "c-s1")
        record_lesson(cat, "test clean", "c-s2")
        record_lesson(cat, "test clean", "c-s3")
        mark_lesson_improving(cat, f"{cat}-pos-1", evidence="obs")
        mark_lesson_improving(cat, f"{cat}-pos-2", evidence="obs")

        self._prepare_gates(cat, days_ago=LESSON_MIN_RESOLUTION_DAYS + 1)

        auto_resolve_lessons()
        lessons = get_lessons(category=cat)
        assert lessons[0]["status"] == STATUS_RESOLVED, (
            f"never-regressed lesson should reach plain RESOLVED; got {lessons[0]['status']}"
        )
        assert lessons[0]["status"] != STATUS_RESOLVED_WITH_HISTORY, (
            "RESOLVED_WITH_HISTORY leaked to a lesson with zero regressions — "
            "pre-reg falsifier (1) fires"
        )
        assert lessons[0].get("regressions", 0) == 0

    def test_regressed_lesson_without_evidence_stays_improving(self):
        """No evidence = no exit, even with cooldown satisfied. The fix
        gives regressed lessons a path; it does not open the gate for
        them to skip the evidence requirement."""
        from divineos.core.constants import LESSON_MIN_RESOLUTION_DAYS
        from divineos.core.knowledge.lessons import (
            LESSON_REGRESSION_COOLDOWN_DAYS,
            STATUS_IMPROVING,
            STATUS_RESOLVED_WITH_HISTORY,
        )

        cat = "test_rwh_no_evidence"
        self._build_regressed_lesson(cat, n_regressions=1)
        # Advance toward improving via absence-only (no evidence arg).
        mark_lesson_improving(cat, f"{cat}-abs-1")
        mark_lesson_improving(cat, f"{cat}-abs-2")

        days_ago = max(LESSON_MIN_RESOLUTION_DAYS, LESSON_REGRESSION_COOLDOWN_DAYS) + 1
        self._prepare_gates(cat, days_ago=days_ago)

        transitioned = auto_resolve_lessons()
        transitioned_cats = [lesson["category"] for lesson in transitioned]
        assert cat not in transitioned_cats, (
            "regressed lesson without positive evidence should not transition"
        )

        lessons = get_lessons(category=cat)
        assert lessons[0]["status"] == STATUS_IMPROVING
        assert lessons[0]["status"] != STATUS_RESOLVED_WITH_HISTORY

    def test_resolved_with_history_constant_is_distinct(self):
        """Module-level invariant: the new state value must not collide
        with existing statuses. Collision would make DB queries filter
        the wrong rows."""
        from divineos.core.knowledge.lessons import (
            STATUS_ACTIVE,
            STATUS_DORMANT,
            STATUS_IMPROVING,
            STATUS_RESOLVED,
            STATUS_RESOLVED_WITH_HISTORY,
        )

        all_statuses = {
            STATUS_ACTIVE,
            STATUS_IMPROVING,
            STATUS_DORMANT,
            STATUS_RESOLVED,
            STATUS_RESOLVED_WITH_HISTORY,
        }
        assert len(all_statuses) == 5, "status constants must be distinct string values"
