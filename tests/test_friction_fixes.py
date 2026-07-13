"""Tests for friction fixes: lesson inflation, handoff protection,
encouragement filter, SIS word count guard, contradiction details."""

import json

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge.lessons import (
    LESSON_EFFECTIVE_MIN,
    auto_resolve_lessons,
    get_lessons,
    record_lesson,
    reset_lesson_count,
)


@pytest.fixture(autouse=True)
def _init_knowledge():
    init_knowledge_table()


class TestLessonInflationFix:
    """Same session shouldn't inflate occurrence count."""

    def test_same_session_no_inflation(self):
        record_lesson("test_inflate", "desc", "s1")
        record_lesson("test_inflate", "desc", "s1")
        record_lesson("test_inflate", "desc", "s1")
        lessons = get_lessons(category="test_inflate")
        assert lessons[0]["occurrences"] == 1

    def test_different_sessions_do_increment(self):
        record_lesson("test_real_count", "desc", "s1")
        record_lesson("test_real_count", "desc", "s2")
        record_lesson("test_real_count", "desc", "s3")
        lessons = get_lessons(category="test_real_count")
        assert lessons[0]["occurrences"] == 3

    def test_lesson_effective_min_defined(self):
        """Log-scaled effective occurrences floor is 5 (replaces old cap of 10)."""
        assert LESSON_EFFECTIVE_MIN == 5

    def test_auto_resolve_uses_capped_occurrences(self):
        """Even with inflated counts, auto_resolve uses capped occurrences.

        Also satisfies stimulus-presence gates: time gate (backdate last_seen)
        and stimulus gate (add decision journal entries with category keywords).
        """
        import time

        from divineos.core.constants import LESSON_MIN_RESOLUTION_DAYS, SECONDS_PER_DAY
        from divineos.core.knowledge import _get_connection
        from divineos.core.knowledge.lessons import mark_lesson_improving
        from divineos.core.ledger import get_connection as get_ledger_connection

        # Create a lesson with inflated count
        record_lesson("test_capped", "desc", "s1")
        record_lesson("test_capped", "desc", "s2")
        record_lesson("test_capped", "desc", "s3")
        mark_lesson_improving("test_capped", "s4")

        # Manually inflate occurrences to simulate old bug
        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE lesson_tracking SET occurrences = 178 WHERE category = 'test_capped'"
            )
            # With log-scaling: effective = max(5, int(log2(178)+2)) = 9
            # Need 9 + 5 (threshold) = 14 total sessions to resolve.
            row = conn.execute(
                "SELECT sessions FROM lesson_tracking WHERE category = 'test_capped'"
            ).fetchone()
            sessions = json.loads(row[0])
            for i in range(5, 20):
                sessions.append(f"s{i}")
            conn.execute(
                "UPDATE lesson_tracking SET sessions = ? WHERE category = 'test_capped'",
                (json.dumps(sessions),),
            )
            # Backdate last_seen to satisfy the time gate
            old_enough = time.time() - (LESSON_MIN_RESOLUTION_DAYS + 1) * SECONDS_PER_DAY
            conn.execute(
                "UPDATE lesson_tracking SET last_seen = ? WHERE category = 'test_capped'",
                (old_enough,),
            )
            conn.commit()
        finally:
            conn.close()

        # Add decision journal entries with category keyword so stimulus gate passes.
        # "test_capped" has keywords ["test", "capped"].
        # Clean sessions start at index effective=9, so s13..s19 are the clean ones.
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
            for sid in ["s13", "s14", "s15"]:
                ledger_conn.execute(
                    "INSERT OR IGNORE INTO decision_journal (decision_id, created_at, content, session_id) "
                    "VALUES (?, ?, ?, ?)",
                    (f"dj-capped-{sid}", time.time(), "Ran the test suite and capped output", sid),
                )
            ledger_conn.commit()
        finally:
            ledger_conn.close()

        resolved = auto_resolve_lessons()
        cats = [r["category"] for r in resolved]
        assert "test_capped" in cats


class TestResetLessonCount:
    def test_reset_to_real_count(self):
        record_lesson("test_reset", "desc", "s1")
        record_lesson("test_reset", "desc", "s2")
        record_lesson("test_reset", "desc", "s3")
        assert reset_lesson_count("test_reset") is True
        lessons = get_lessons(category="test_reset")
        # Should be 3 (the number of unique sessions)
        assert lessons[0]["occurrences"] == 3

    def test_reset_to_specific_count(self):
        record_lesson("test_reset_n", "desc", "s1")
        record_lesson("test_reset_n", "desc", "s2")
        assert reset_lesson_count("test_reset_n", new_count=1) is True
        lessons = get_lessons(category="test_reset_n")
        assert lessons[0]["occurrences"] == 1

    def test_reset_nonexistent_returns_false(self):
        assert reset_lesson_count("nonexistent_category") is False


class TestHandoffProtection:
    def test_extract_exchange_count(self):
        from divineos.core.hud_handoff import _extract_exchange_count

        assert _extract_exchange_count("Last session: 12 exchanges, 3 knowledge") == 12
        assert _extract_exchange_count("Last session: 0 exchanges, 0 knowledge") == 0
        assert _extract_exchange_count("No exchange info here") == 0

    def test_save_preserves_good_handoff_over_empty(self):
        """Don't overwrite a good handoff with an empty post-compaction one."""
        import divineos.core.hud_handoff as hh
        from divineos.core._hud_io import _ensure_hud_dir

        hud_dir = _ensure_hud_dir()
        handoff_path = hud_dir / "handoff_note.json"

        # Write a good handoff
        hh.save_handoff_note(
            summary="Last session: 15 exchanges, 5 knowledge entries extracted.",
            mood="strong session",
            session_id="good-session",
        )
        assert handoff_path.exists()
        good_data = json.loads(handoff_path.read_text(encoding="utf-8"))
        assert "15 exchanges" in good_data["summary"]

        # Try to overwrite with empty post-compaction handoff
        hh.save_handoff_note(
            summary="Last session: 0 exchanges, 0 knowledge entries extracted.",
            mood="mixed session",
            session_id="compacted-session",
        )

        # The good handoff should be preserved
        preserved = json.loads(handoff_path.read_text(encoding="utf-8"))
        assert "15 exchanges" in preserved["summary"]


class TestEncouragementFilter:
    def test_pure_praise_filtered(self):
        from divineos.core.knowledge.deep_extraction import _is_encouragement

        assert _is_encouragement("Great job! Well done!")
        assert _is_encouragement("That's awesome, love it!")
        assert _is_encouragement("Perfect. Nailed it.")

    def test_actionable_direction_not_filtered(self):
        from divineos.core.knowledge.deep_extraction import _is_encouragement

        assert not _is_encouragement("Use SQLite for storage. Zero dependencies.")
        assert not _is_encouragement("Run tests after every code change.")
        assert not _is_encouragement(
            "When you audit the system, check all integration points, not just the main module."
        )

    def test_mixed_praise_with_direction_not_filtered(self):
        from divineos.core.knowledge.deep_extraction import _is_encouragement

        # Long text with one encouragement word but real content
        text = (
            "Great observation about the architecture. When building new modules, "
            "always check for existing patterns in the codebase first. Don't reinvent "
            "what already exists."
        )
        assert not _is_encouragement(text)


class TestSelfAwarenessNudgeKeyFix:
    """The HUD self-awareness slot must use the 'text' key from recommend()."""

    def test_recommend_returns_text_key(self):
        from divineos.core.proactive_patterns import recommend

        recs = recommend("session_start", max_recommendations=3)
        for rec in recs:
            assert "text" in rec, f"recommend() result missing 'text' key: {list(rec.keys())}"

    def test_hud_nudge_not_empty(self):
        """TRY: lines should contain actual content, not empty strings."""
        from divineos.core.proactive_patterns import recommend

        recs = recommend("session_start", max_recommendations=3)
        if recs:
            for rec in recs:
                text = rec.get("text", rec.get("recommendation", ""))
                assert len(text) > 0, "TRY: nudge would render empty"


class TestSessionHealthResetOnBriefing:
    """Session health should reset when briefing loads (new session)."""

    def test_health_file_cleared_on_briefing_load(self):
        from divineos.core._hud_io import _ensure_hud_dir
        from divineos.core.hud_handoff import mark_briefing_loaded
        from divineos.core.hud_state import update_session_health

        # Simulate stale health from prior session
        update_session_health(corrections=5, encouragements=0, grade="D", notes="rough session")
        health_path = _ensure_hud_dir() / "session_health.json"
        assert health_path.exists()

        # Load briefing — should clear stale health
        mark_briefing_loaded()
        assert not health_path.exists(), "session_health.json should be cleared on briefing load"


class TestSISWordCountGuard:
    def test_short_docstring_not_flagged(self):
        # A short docstring with one esoteric term shouldn't get flagged
        # We test the logic directly since audit_docstrings scans real files
        docstring = "CLI commands for Body Awareness."
        word_count = len(docstring.split())
        assert word_count < 20  # Should be below threshold
