"""Tests for the defeated-warrant-to-lesson pipeline."""

import pytest

from divineos.core.logic.logic_validation import (
    check_defeat_pattern,
    record_defeat_lesson,
    scan_defeated_only_entries,
)
from divineos.core.logic.warrants import (
    create_warrant,
    defeat_warrant,
    init_warrant_table,
)


@pytest.fixture(autouse=True)
def _temp_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DIVINEOS_DB", db_path)
    from divineos.core.knowledge import init_knowledge_table

    init_knowledge_table()
    init_warrant_table()
    # Ensure lessons table exists
    yield


def _insert_knowledge(kid="test-knowledge-1", content="Test knowledge content"):
    """Helper to insert a knowledge row for warrant tests."""
    import hashlib

    from divineos.core.knowledge import get_connection

    content_hash = hashlib.sha256(content.encode()).hexdigest()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO knowledge "
            "(knowledge_id, knowledge_type, content, confidence, access_count, "
            "created_at, updated_at, source_events, tags, maturity, content_hash) "
            "VALUES (?, 'FACT', ?, 0.8, 0, strftime('%s','now'), strftime('%s','now'), '[]', '[]', 'RAW', ?)",
            (kid, content, content_hash),
        )
        conn.commit()
    finally:
        conn.close()


class TestCheckDefeatPattern:
    def test_no_pattern_with_single_defeat(self):
        kid = "test-knowledge-single"
        _insert_knowledge(kid)
        w = create_warrant(kid, "EMPIRICAL", "test results showed X")
        defeat_warrant(w.warrant_id, "contradicted by new test")
        # Only 1 defeated warrant — no pattern yet
        result = check_defeat_pattern(kid, "EMPIRICAL")
        assert result is None

    def test_pattern_detected_with_two_defeats(self):
        kid = "test-knowledge-pattern"
        _insert_knowledge(kid, "Claim about database performance")
        w1 = create_warrant(kid, "EMPIRICAL", "benchmark showed fast")
        w2 = create_warrant(kid, "EMPIRICAL", "second benchmark also showed fast")
        defeat_warrant(w1.warrant_id, "new benchmark contradicts")
        defeat_warrant(w2.warrant_id, "another benchmark contradicts")
        result = check_defeat_pattern(kid, "EMPIRICAL")
        assert result is not None  # lesson_id returned
        assert len(result) == 36  # UUID

    def test_different_warrant_types_no_pattern(self):
        kid = "test-knowledge-mixed"
        _insert_knowledge(kid)
        w1 = create_warrant(kid, "EMPIRICAL", "test showed X")
        w2 = create_warrant(kid, "TESTIMONIAL", "user said X")
        defeat_warrant(w1.warrant_id, "contradicted")
        defeat_warrant(w2.warrant_id, "contradicted")
        # Different types — no pattern for either type alone
        result_emp = check_defeat_pattern(kid, "EMPIRICAL")
        result_test = check_defeat_pattern(kid, "TESTIMONIAL")
        assert result_emp is None
        assert result_test is None


class TestRecordDefeatLesson:
    def test_creates_lesson(self):
        _insert_knowledge("test-lesson-kid")
        lesson_id = record_defeat_lesson(
            knowledge_id="test-lesson-kid",
            warrant_type="EMPIRICAL",
            defeat_count=3,
            topic_hint="database performance claims",
        )
        assert lesson_id
        # Verify the lesson exists
        from divineos.core.knowledge.lessons import get_lessons

        lessons = get_lessons()
        assert any("EMPIRICAL" in lesson["description"] for lesson in lessons)

    def test_lesson_description_includes_details(self):
        _insert_knowledge("test-desc-kid")
        record_defeat_lesson(
            knowledge_id="test-desc-kid",
            warrant_type="TESTIMONIAL",
            defeat_count=2,
            topic_hint="user preference about formatting",
        )
        from divineos.core.knowledge.lessons import get_lessons

        lessons = get_lessons()
        found = [lesson for lesson in lessons if "TESTIMONIAL" in lesson["description"]]
        assert len(found) == 1
        assert "2x" in found[0]["description"]


class TestScanDefeatedOnly:
    def test_empty_when_no_warrants(self):
        results = scan_defeated_only_entries()
        assert results == []

    def test_finds_defeated_only_entries(self):
        kid = "test-defeated-only"
        _insert_knowledge(kid, "Some claim that lost all support")
        w = create_warrant(kid, "EMPIRICAL", "test showed X")
        defeat_warrant(w.warrant_id, "new evidence contradicts")
        results = scan_defeated_only_entries()
        assert len(results) == 1
        assert results[0]["knowledge_id"] == kid

    def test_ignores_entries_with_active_warrants(self):
        kid = "test-still-active"
        _insert_knowledge(kid, "Claim with mixed warrants")
        w1 = create_warrant(kid, "EMPIRICAL", "test showed X")
        create_warrant(kid, "TESTIMONIAL", "user confirmed X")
        defeat_warrant(w1.warrant_id, "contradicted")
        # w2 still active
        results = scan_defeated_only_entries()
        defeated_ids = [r["knowledge_id"] for r in results]
        assert kid not in defeated_ids
