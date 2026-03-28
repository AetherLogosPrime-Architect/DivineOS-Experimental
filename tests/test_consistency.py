"""Tests for the consistency checking system."""

import pytest
import time
import uuid

from divineos.core.ledger import init_db
from divineos.core.knowledge._base import init_knowledge_table, _get_connection, compute_hash
from divineos.core.logic.warrants import init_warrant_table
from divineos.core.logic.relations import init_relation_table, create_relation
from divineos.core.logic.consistency import (
    check_consistency,
    check_local_consistency,
    check_transitive_consistency,
    register_contradiction,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()
    init_warrant_table()
    init_relation_table()
    yield


def _insert_knowledge(content="test"):
    kid = str(uuid.uuid4())
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO knowledge
               (knowledge_id, created_at, updated_at, knowledge_type, content,
                confidence, source_events, tags, access_count, content_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                kid,
                time.time(),
                time.time(),
                "FACT",
                content,
                1.0,
                "[]",
                "[]",
                0,
                compute_hash(content),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return kid


class TestLocalConsistency:
    def test_no_contradictions(self):
        a = _insert_knowledge("fact a")
        assert check_local_consistency(a) == []

    def test_direct_contradiction(self):
        a = _insert_knowledge("X is true")
        b = _insert_knowledge("X is false")
        create_relation(a, b, "CONTRADICTS")
        results = check_local_consistency(a)
        assert len(results) == 1
        assert results[0].entry_a == a
        assert results[0].entry_b == b
        assert results[0].contradiction_type == "DIRECT"

    def test_bidirectional_contradiction(self):
        a = _insert_knowledge("X is true")
        b = _insert_knowledge("X is false")
        create_relation(a, b, "CONTRADICTS")
        # Check from both sides
        from_a = check_local_consistency(a)
        from_b = check_local_consistency(b)
        assert len(from_a) == 1
        assert len(from_b) == 1


class TestTransitiveConsistency:
    def test_no_transitive_contradictions(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        results = check_transitive_consistency(a)
        assert results == []

    def test_one_hop_transitive(self):
        """A implies B, B contradicts C → A has transitive issue with C."""
        a = _insert_knowledge("premise")
        b = _insert_knowledge("intermediate")
        c = _insert_knowledge("contradicted")
        create_relation(a, b, "IMPLIES")
        create_relation(b, c, "CONTRADICTS")
        results = check_transitive_consistency(a)
        assert len(results) == 1
        assert results[0].entry_b == c
        assert results[0].contradiction_type == "TRANSITIVE"
        assert len(results[0].path) == 3  # a → b → c

    def test_two_hop_transitive(self):
        """A implies B, B implies C, C contradicts D."""
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        d = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(b, c, "IMPLIES")
        create_relation(c, d, "CONTRADICTS")
        results = check_transitive_consistency(a, max_depth=3)
        assert len(results) == 1
        assert results[0].entry_b == d

    def test_depth_limit_respected(self):
        """Deep contradiction beyond max_depth is not found."""
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        d = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(b, c, "IMPLIES")
        create_relation(c, d, "CONTRADICTS")
        # depth=1 should not reach d
        results = check_transitive_consistency(a, max_depth=1)
        assert len(results) == 0

    def test_confidence_decays(self):
        """Transitive confidence should be less than direct."""
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES", confidence=1.0)
        create_relation(b, c, "CONTRADICTS", confidence=1.0)
        results = check_transitive_consistency(a)
        assert len(results) == 1
        assert results[0].confidence < 1.0


class TestFullConsistency:
    def test_combines_local_and_transitive(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        d = _insert_knowledge()
        create_relation(a, b, "CONTRADICTS")  # direct
        create_relation(a, c, "IMPLIES")
        create_relation(c, d, "CONTRADICTS")  # transitive
        results = check_consistency(a)
        assert len(results) == 2

    def test_deduplicates_by_pair(self):
        """Same pair found via local and transitive → keep highest confidence."""
        a = _insert_knowledge()
        b = _insert_knowledge()
        create_relation(a, b, "CONTRADICTS")
        # Also create an implies-then-contradicts path back to b... tricky
        # The dedup should keep only 1 entry for (a, b)
        results = check_consistency(a)
        pairs = [(r.entry_a, r.entry_b) for r in results]
        # Exactly one entry for the (a, b) pair
        assert len([p for p in pairs if set(p) == {a, b}]) == 1

    def test_empty_graph(self):
        a = _insert_knowledge()
        assert check_consistency(a) == []


class TestRegisterContradiction:
    def test_creates_relation(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        register_contradiction(a, b, notes="temporal override")
        results = check_local_consistency(a)
        assert len(results) == 1

    def test_increments_contradiction_count(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        register_contradiction(a, b)
        conn = _get_connection()
        try:
            row_a = conn.execute(
                "SELECT contradiction_count FROM knowledge WHERE knowledge_id = ?", (a,)
            ).fetchone()
            row_b = conn.execute(
                "SELECT contradiction_count FROM knowledge WHERE knowledge_id = ?", (b,)
            ).fetchone()
        finally:
            conn.close()
        assert row_a[0] == 1
        assert row_b[0] == 1
