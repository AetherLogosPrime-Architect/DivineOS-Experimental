"""Tests for warrant backfill — retroactive INHERITED warrants for pre-existing entries."""

import hashlib

import pytest

from divineos.core.logic.logic_reasoning import backfill_inherited_warrants
from divineos.core.logic.warrants import create_warrant, get_warrants, init_warrant_table


@pytest.fixture(autouse=True)
def _temp_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DIVINEOS_DB", db_path)
    from divineos.core.knowledge import init_knowledge_table

    init_knowledge_table()
    init_warrant_table()
    yield


def _insert_knowledge(kid, content="Test content"):
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


class TestBackfillInheritedWarrants:
    def test_backfills_unwarranted_entries(self):
        _insert_knowledge("k1", "First fact")
        _insert_knowledge("k2", "Second fact")
        counts = backfill_inherited_warrants()
        assert counts["checked"] == 2
        assert counts["backfilled"] == 2
        assert counts["already_warranted"] == 0
        # Verify warrants were created
        w1 = get_warrants("k1")
        assert len(w1) == 1
        assert w1[0].warrant_type == "INHERITED"
        assert w1[0].status == "ACTIVE"

    def test_skips_already_warranted(self):
        _insert_knowledge("k1", "Has a warrant")
        create_warrant("k1", "EMPIRICAL", "test evidence")
        _insert_knowledge("k2", "No warrant")
        counts = backfill_inherited_warrants()
        assert counts["already_warranted"] == 1
        assert counts["backfilled"] == 1

    def test_dry_run_creates_nothing(self):
        _insert_knowledge("k1", "Should not get warrant")
        counts = backfill_inherited_warrants(dry_run=True)
        assert counts["backfilled"] == 1
        # But no warrant actually created
        assert get_warrants("k1") == []

    def test_empty_database(self):
        counts = backfill_inherited_warrants()
        assert counts["checked"] == 0
        assert counts["backfilled"] == 0

    def test_idempotent(self):
        _insert_knowledge("k1", "Fact")
        backfill_inherited_warrants()
        # Run again — should not create duplicates
        counts = backfill_inherited_warrants()
        assert counts["backfilled"] == 0
        assert counts["already_warranted"] == 1
        assert len(get_warrants("k1")) == 1
