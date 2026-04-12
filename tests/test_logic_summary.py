"""Tests for logic_summary — warrant chain display and logic health stats."""

import pytest

from divineos.core.logic.logic_session import (
    format_logic_health_line,
    format_warrant_chain,
    get_logic_health_summary,
    get_warrant_chain,
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
    from divineos.core.knowledge.edges import init_edge_table

    init_knowledge_table()
    init_edge_table()
    init_warrant_table()
    yield


def _insert_knowledge(kid, content="Test content"):
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


class TestGetWarrantChain:
    def test_empty_for_no_warrants(self):
        _insert_knowledge("no-warrants")
        chain = get_warrant_chain("no-warrants")
        assert chain == []

    def test_returns_warrant_info(self):
        _insert_knowledge("has-warrants")
        create_warrant("has-warrants", "EMPIRICAL", "test showed X")
        create_warrant("has-warrants", "TESTIMONIAL", "user confirmed X")
        chain = get_warrant_chain("has-warrants")
        assert len(chain) == 2
        types = {w["warrant_type"] for w in chain}
        assert types == {"EMPIRICAL", "TESTIMONIAL"}

    def test_shows_defeated_status(self):
        _insert_knowledge("mixed-warrants")
        w1 = create_warrant("mixed-warrants", "EMPIRICAL", "test showed X")
        create_warrant("mixed-warrants", "TESTIMONIAL", "user said X")
        defeat_warrant(w1.warrant_id, "contradicted")
        chain = get_warrant_chain("mixed-warrants")
        statuses = {w["warrant_type"]: w["status"] for w in chain}
        assert statuses["EMPIRICAL"] == "DEFEATED"
        assert statuses["TESTIMONIAL"] == "ACTIVE"


class TestFormatWarrantChain:
    def test_empty_returns_empty(self):
        assert format_warrant_chain([]) == ""

    def test_formats_active_warrants(self):
        warrants = [
            {"warrant_type": "EMPIRICAL", "grounds": "test", "status": "ACTIVE"},
            {"warrant_type": "TESTIMONIAL", "grounds": "user", "status": "ACTIVE"},
        ]
        result = format_warrant_chain(warrants)
        assert "EMPIRICAL +" in result
        assert "TESTIMONIAL +" in result
        assert "warrants:" in result

    def test_formats_defeated_warrants(self):
        warrants = [
            {"warrant_type": "EMPIRICAL", "grounds": "test", "status": "DEFEATED"},
        ]
        result = format_warrant_chain(warrants)
        assert "EMPIRICAL x" in result


class TestLogicHealthSummary:
    def test_empty_database(self):
        stats = get_logic_health_summary()
        assert stats["total_entries"] == 0
        assert stats["unwarranted"] == 0
        assert stats["contradictions"] == 0

    def test_counts_unwarranted(self):
        _insert_knowledge("unwarranted-1", "No warrant for this")
        _insert_knowledge("unwarranted-2", "No warrant for this either")
        _insert_knowledge("warranted-1", "Has a warrant")
        create_warrant("warranted-1", "EMPIRICAL", "evidence")
        stats = get_logic_health_summary()
        assert stats["total_entries"] == 3
        assert stats["unwarranted"] == 2

    def test_counts_defeated_only(self):
        _insert_knowledge("all-defeated", "Lost all support")
        w = create_warrant("all-defeated", "EMPIRICAL", "old evidence")
        defeat_warrant(w.warrant_id, "contradicted")
        stats = get_logic_health_summary()
        assert stats["defeated_only"] == 1


class TestFormatLogicHealthLine:
    def test_empty_when_clean(self):
        stats = {"unwarranted": 0, "defeated_only": 0, "contradictions": 0}
        assert format_logic_health_line(stats) == ""

    def test_shows_unwarranted(self):
        stats = {"unwarranted": 3, "defeated_only": 0, "contradictions": 0}
        assert "3 unwarranted" in format_logic_health_line(stats)

    def test_shows_all_issues(self):
        stats = {"unwarranted": 2, "defeated_only": 1, "contradictions": 3}
        line = format_logic_health_line(stats)
        assert "2 unwarranted" in line
        assert "1 lost all justification" in line
        assert "3 contradictions" in line
