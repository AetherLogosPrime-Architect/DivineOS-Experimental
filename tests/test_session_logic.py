"""Tests for session_logic — the SESSION_END logic orchestration."""

import pytest

from divineos.core.logic.logic_session import (
    LogicPassResult,
    format_logic_summary,
    run_session_logic_pass,
)
from divineos.core.logic.warrants import create_warrant, init_warrant_table


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


def _insert_knowledge(kid, content="Test content", maturity="RAW"):
    import hashlib

    from divineos.core.knowledge import get_connection

    content_hash = hashlib.sha256(content.encode()).hexdigest()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO knowledge "
            "(knowledge_id, knowledge_type, content, confidence, access_count, "
            "created_at, updated_at, source_events, tags, maturity, content_hash) "
            "VALUES (?, 'FACT', ?, 0.8, 0, strftime('%s','now'), strftime('%s','now'), '[]', '[]', ?, ?)",
            (kid, content, maturity, content_hash),
        )
        conn.commit()
    finally:
        conn.close()


class TestLogicPassResult:
    def test_defaults(self):
        r = LogicPassResult()
        assert r.contradictions_found == 0
        assert r.warrants_created == 0
        assert r.inferences_made == 0
        assert r.entries_checked == 0
        assert r.details == []


class TestRunSessionLogicPass:
    def test_empty_ids(self):
        result = run_session_logic_pass([])
        assert result.entries_checked == 0
        assert result.contradictions_found == 0

    def test_checks_entries(self):
        _insert_knowledge("k1", "The sky is blue")
        _insert_knowledge("k2", "Water flows downhill")
        result = run_session_logic_pass(["k1", "k2"])
        assert result.entries_checked == 2

    def test_respects_max_entries(self):
        for i in range(10):
            _insert_knowledge(f"k{i}", f"Knowledge {i}")
        ids = [f"k{i}" for i in range(10)]
        result = run_session_logic_pass(ids, max_entries=3)
        assert result.entries_checked == 3

    def test_defeated_only_scan_runs(self):
        # Create a knowledge entry with only a defeated warrant
        _insert_knowledge("kd", "Defeated claim")
        w = create_warrant("kd", "EMPIRICAL", "test showed X")
        from divineos.core.logic.warrants import defeat_warrant

        defeat_warrant(w.warrant_id, "contradicted")
        result = run_session_logic_pass(["kd"])
        assert result.defeated_only_count >= 1


class TestFormatLogicSummary:
    def test_clean_result(self):
        r = LogicPassResult(entries_checked=5)
        assert "5 entries checked, clean" in format_logic_summary(r)

    def test_contradictions_shown(self):
        r = LogicPassResult(contradictions_found=2)
        assert "2 contradictions" in format_logic_summary(r)

    def test_inferences_shown(self):
        r = LogicPassResult(inferences_made=3)
        assert "3 inferences" in format_logic_summary(r)

    def test_unjustified_shown(self):
        r = LogicPassResult(defeated_only_count=1)
        assert "1 unjustified" in format_logic_summary(r)

    def test_combined(self):
        r = LogicPassResult(contradictions_found=1, inferences_made=2, defeated_only_count=3)
        summary = format_logic_summary(r)
        assert "1 contradictions" in summary
        assert "2 inferences" in summary
        assert "3 unjustified" in summary
