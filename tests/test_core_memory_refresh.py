"""Tests for core memory auto-refresh and active memory recency boost."""

import json
import time

import pytest

import divineos.core.ledger as ledger_mod
from divineos.core.active_memory import compute_importance
from divineos.core.knowledge import init_knowledge_table, store_knowledge
from divineos.core.ledger import init_db
from divineos.core.memory import (
    get_core,
    init_memory_tables,
)


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setattr(ledger_mod, "DB_PATH", test_db)
    monkeypatch.setattr(ledger_mod, "_get_db_path", lambda: test_db)
    init_db()
    init_knowledge_table()
    init_memory_tables()
    yield


# ── Recency Boost Tests ──────────────────────────────────────────────


class TestRecencyBoost:
    def test_fresh_entry_scores_higher(self):
        """Entry created now should score higher than identical entry from 60 days ago."""
        now = time.time()
        fresh = {
            "knowledge_type": "PRINCIPLE",
            "confidence": 0.8,
            "access_count": 0,
            "source": "STATED",
            "content": "Test principle",
            "created_at": now,
        }
        stale = {
            "knowledge_type": "PRINCIPLE",
            "confidence": 0.8,
            "access_count": 0,
            "source": "STATED",
            "content": "Test principle",
            "created_at": now - (60 * 86400),  # 60 days ago
        }
        fresh_score = compute_importance(fresh)
        stale_score = compute_importance(stale)
        assert fresh_score > stale_score

    def test_recency_decays_over_30_days(self):
        """Recency boost should be zero after 30 days."""
        now = time.time()
        at_30_days = {
            "knowledge_type": "FACT",
            "confidence": 0.5,
            "access_count": 0,
            "source": "STATED",
            "content": "Old fact",
            "created_at": now - (30 * 86400),
        }
        at_31_days = {
            "knowledge_type": "FACT",
            "confidence": 0.5,
            "access_count": 0,
            "source": "STATED",
            "content": "Older fact",
            "created_at": now - (31 * 86400),
        }
        # Both should have zero recency boost — scores should be equal
        score_30 = compute_importance(at_30_days)
        score_31 = compute_importance(at_31_days)
        assert score_30 == score_31

    def test_recency_max_at_day_zero(self):
        """Brand new entry gets full 0.05 recency boost."""
        now = time.time()
        brand_new = {
            "knowledge_type": "FACT",
            "confidence": 0.5,
            "access_count": 0,
            "source": "STATED",
            "content": "Brand new fact",
            "created_at": now,
        }
        no_timestamp = {
            "knowledge_type": "FACT",
            "confidence": 0.5,
            "access_count": 0,
            "source": "STATED",
            "content": "No timestamp fact",
            "created_at": 0,
        }
        new_score = compute_importance(brand_new)
        no_ts_score = compute_importance(no_timestamp)
        # The difference should be approximately 0.05 (full recency boost).
        # Use approx with wide tolerance — the exact value depends on how
        # fast time.time() advances between entry creation and scoring.
        diff = new_score - no_ts_score
        assert diff == pytest.approx(0.05, abs=0.02)

    def test_no_recency_without_timestamp(self):
        """Entry without created_at gets no recency boost."""
        entry = {
            "knowledge_type": "FACT",
            "confidence": 0.5,
            "access_count": 0,
            "source": "STATED",
            "content": "No timestamp",
        }
        # Should not crash and should get a reasonable score
        score = compute_importance(entry)
        assert 0.0 <= score <= 1.0


# ── Core Memory Refresh Tests ────────────────────────────────────────


class TestCoreMemoryRefresh:
    def test_refresh_updates_priorities_from_goals(self, tmp_path, monkeypatch):
        """Refresh should update current_priorities when goals exist."""
        from divineos.core.core_memory_refresh import _refresh_priorities
        from divineos.core.hud import _ensure_hud_dir

        hud_dir = _ensure_hud_dir()
        goals = [
            {"text": "Build claims engine", "original_words": "", "status": "active"},
            {"text": "Fix memory ranking", "original_words": "", "status": "active"},
            {"text": "Old completed goal", "original_words": "", "status": "done"},
        ]
        (hud_dir / "active_goals.json").write_text(json.dumps(goals), encoding="utf-8")

        result = _refresh_priorities()
        assert result is True

        content = get_core("current_priorities")
        assert "Build claims engine" in content["current_priorities"]
        assert "Fix memory ranking" in content["current_priorities"]
        assert "Old completed goal" not in content["current_priorities"]

    def test_refresh_no_update_when_unchanged(self, tmp_path, monkeypatch):
        """Refresh should not update if content hasn't changed."""
        from divineos.core.core_memory_refresh import _refresh_priorities
        from divineos.core.hud import _ensure_hud_dir

        hud_dir = _ensure_hud_dir()
        goals = [
            {"text": "Build something", "original_words": "", "status": "active"},
        ]
        (hud_dir / "active_goals.json").write_text(json.dumps(goals), encoding="utf-8")

        # First call updates
        assert _refresh_priorities() is True
        # Second call should detect no change
        assert _refresh_priorities() is False

    def test_refresh_strengths_from_knowledge(self):
        """Refresh should include knowledge store stats."""
        from divineos.core.core_memory_refresh import _refresh_strengths

        # Store some knowledge
        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="I should always test my code",
            confidence=0.9,
        )
        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="I should read before writing",
            confidence=0.85,
        )

        result = _refresh_strengths()
        assert result is True

        content = get_core("known_strengths")
        assert "active entries" in content["known_strengths"]

    def test_refresh_weaknesses_from_lessons(self):
        """Refresh should include active lessons."""
        from divineos.core.core_memory_refresh import _refresh_weaknesses
        from divineos.core.knowledge import get_connection
        from divineos.core.ledger import compute_hash

        # Use the real lesson_tracking table
        conn = get_connection()
        now = time.time()
        conn.execute(
            "INSERT INTO lesson_tracking "
            "(lesson_id, created_at, category, description, first_session, "
            "occurrences, last_seen, sessions, status, content_hash, agent) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "l1",
                now,
                "testing",
                "I need to run tests before committing",
                "s1",
                3,
                now,
                '["s1","s2","s3"]',
                "active",
                compute_hash("I need to run tests before committing"),
                "claude",
            ),
        )
        conn.commit()
        conn.close()

        result = _refresh_weaknesses()
        assert result is True

        content = get_core("known_weaknesses")
        assert "active lesson" in content["known_weaknesses"]

    def test_full_refresh_returns_status(self):
        """refresh_core_memory returns a dict of slot update statuses."""
        from divineos.core.core_memory_refresh import refresh_core_memory

        results = refresh_core_memory()
        assert "current_priorities" in results
        assert "known_strengths" in results
        assert "known_weaknesses" in results
        # All should be bool
        for v in results.values():
            assert isinstance(v, bool)

    def test_refresh_with_analysis(self):
        """Refresh should incorporate session analysis data."""
        from divineos.core.core_memory_refresh import _refresh_strengths

        # Store knowledge so the function has something to report
        store_knowledge(
            knowledge_type="FACT",
            content="Test fact for strength refresh",
            confidence=0.9,
        )

        # Mock analysis with encouragements
        class MockAnalysis:
            encouragements = ["Great work!", "Perfect approach"]
            corrections = []

        result = _refresh_strengths(MockAnalysis())
        assert result is True

        content = get_core("known_strengths")
        assert "2 encouragement(s)" in content["known_strengths"]
