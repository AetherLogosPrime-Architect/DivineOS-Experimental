"""Tests for knowledge impact tracking."""

import sqlite3

import pytest

from divineos.core.knowledge_impact import (
    assess_session_impact,
    format_impact_summary,
    get_impact_history,
    init_impact_table,
    record_knowledge_retrieval,
)


@pytest.fixture(autouse=True)
def _clean_impact_table():
    """Ensure clean impact table for each test."""
    init_impact_table()
    from divineos.core.knowledge._base import _get_connection

    conn = _get_connection()
    try:
        conn.execute("DELETE FROM knowledge_impact")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()
    yield


class TestRecordRetrieval:
    def test_returns_impact_id(self):
        iid = record_knowledge_retrieval("sess-1", "k-123", "User prefers concise answers")
        assert iid.startswith("imp-")

    def test_stores_retrieval(self):
        record_knowledge_retrieval("sess-1", "k-123", "User prefers concise answers")
        from divineos.core.knowledge._base import _get_connection

        conn = _get_connection()
        row = conn.execute(
            "SELECT knowledge_id, content_brief FROM knowledge_impact WHERE session_id = ?",
            ("sess-1",),
        ).fetchone()
        conn.close()
        assert row[0] == "k-123"
        assert "concise" in row[1]

    def test_truncates_long_content(self):
        long_content = "x" * 500
        record_knowledge_retrieval("sess-1", "k-123", long_content)
        from divineos.core.knowledge._base import _get_connection

        conn = _get_connection()
        row = conn.execute(
            "SELECT content_brief FROM knowledge_impact WHERE session_id = ?",
            ("sess-1",),
        ).fetchone()
        conn.close()
        assert len(row[0]) <= 200


class TestAssessImpact:
    def test_no_retrievals_returns_clean(self):
        result = assess_session_impact("sess-1", ["wrong answer"])
        assert result["retrieved"] == 0
        assert result["impact_score"] == 1.0

    def test_no_corrections_all_clean(self):
        record_knowledge_retrieval("sess-1", "k-1", "User prefers concise answers")
        record_knowledge_retrieval("sess-1", "k-2", "Always run tests after changes")
        result = assess_session_impact("sess-1", [])
        assert result["retrieved"] == 2
        assert result["clean"] == 2
        assert result["correction_overlaps"] == 0
        assert result["impact_score"] == 1.0

    def test_correction_overlap_detected(self):
        record_knowledge_retrieval(
            "sess-1", "k-1", "User prefers concise short direct answers"
        )
        result = assess_session_impact(
            "sess-1",
            ["Your answer was too verbose, please be more concise short direct"],
        )
        assert result["correction_overlaps"] >= 1
        assert result["impact_score"] < 1.0

    def test_unrelated_correction_no_overlap(self):
        record_knowledge_retrieval("sess-1", "k-1", "Always run pytest after code changes")
        result = assess_session_impact(
            "sess-1",
            ["The variable name should be snake_case"],
        )
        assert result["correction_overlaps"] == 0
        assert result["clean"] == 1

    def test_mixed_results(self):
        record_knowledge_retrieval(
            "sess-1", "k-1", "User prefers concise short direct answers"
        )
        record_knowledge_retrieval(
            "sess-1", "k-2", "Always run pytest after code changes"
        )
        result = assess_session_impact(
            "sess-1",
            ["Your answer was too long, please give concise short direct responses"],
        )
        # k-1 should overlap (concise/short/direct), k-2 should not
        assert result["retrieved"] == 2
        assert result["correction_overlaps"] >= 1
        assert result["clean"] >= 1


class TestImpactHistory:
    def test_empty_history(self):
        h = get_impact_history()
        assert h["total_tracked"] == 0
        assert h["effectiveness"] == 1.0

    def test_aggregates_across_sessions(self):
        record_knowledge_retrieval("sess-1", "k-1", "Always run tests after changes")
        assess_session_impact("sess-1", [])
        record_knowledge_retrieval("sess-2", "k-2", "Always run tests after changes")
        assess_session_impact("sess-2", [])
        h = get_impact_history()
        assert h["total_tracked"] == 2
        assert h["clean"] == 2


class TestFormatSummary:
    def test_no_data(self):
        s = format_impact_summary()
        assert "No knowledge impact data" in s

    def test_with_data(self):
        record_knowledge_retrieval("sess-1", "k-1", "Some knowledge entry here")
        assess_session_impact("sess-1", [])
        s = format_impact_summary()
        assert "100%" in s
