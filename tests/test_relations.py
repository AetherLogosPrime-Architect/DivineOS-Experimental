"""Tests for the logical relations system."""

import time
import uuid

import pytest

from divineos.core.knowledge import _get_connection, compute_hash, init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.logic.logic_reasoning import (
    INVERSE_RELATIONS,
    RELATION_TYPES,
    create_relation,
    deactivate_relation,
    find_relation,
    get_neighbors,
    get_relations,
    init_relation_table,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()
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


class TestCreateRelation:
    def test_create_implies(self):
        a = _insert_knowledge("premise")
        b = _insert_knowledge("conclusion")
        rel = create_relation(a, b, "IMPLIES")
        assert rel.source_id == a
        assert rel.target_id == b
        assert rel.relation_type == "IMPLIES"
        assert rel.status == "ACTIVE"

    def test_all_relation_types(self):
        for rtype in RELATION_TYPES:
            a = _insert_knowledge(f"a-{rtype}")
            b = _insert_knowledge(f"b-{rtype}")
            rel = create_relation(a, b, rtype)
            assert rel.relation_type == rtype

    def test_invalid_type_raises(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        with pytest.raises(ValueError, match="Invalid relation type"):
            create_relation(a, b, "VIBES")

    def test_self_relation_raises(self):
        a = _insert_knowledge()
        with pytest.raises(ValueError, match="itself"):
            create_relation(a, a, "IMPLIES")

    def test_invalid_confidence_raises(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        with pytest.raises(ValueError, match="Confidence"):
            create_relation(a, b, "IMPLIES", confidence=1.5)

    def test_duplicate_returns_existing(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        r1 = create_relation(a, b, "IMPLIES")
        r2 = create_relation(a, b, "IMPLIES")
        assert r1.relation_id == r2.relation_id

    def test_different_types_not_duplicate(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        r1 = create_relation(a, b, "IMPLIES")
        r2 = create_relation(a, b, "SUPPORTS")
        assert r1.relation_id != r2.relation_id


class TestGetRelations:
    def test_outgoing(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(a, c, "SUPPORTS")
        rels = get_relations(a, direction="outgoing")
        assert len(rels) == 2

    def test_incoming(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        rels = get_relations(b, direction="incoming")
        assert len(rels) == 1
        assert rels[0].source_id == a

    def test_both_directions(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(c, a, "SUPPORTS")
        rels = get_relations(a, direction="both")
        assert len(rels) == 2

    def test_filter_by_type(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(a, c, "SUPPORTS")
        rels = get_relations(a, direction="outgoing", relation_type="IMPLIES")
        assert len(rels) == 1
        assert rels[0].target_id == b


class TestFindRelation:
    def test_find_existing(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        create_relation(a, b, "CONTRADICTS")
        found = find_relation(a, b, "CONTRADICTS")
        assert found is not None

    def test_find_nonexistent(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        assert find_relation(a, b, "IMPLIES") is None


class TestDeactivateRelation:
    def test_deactivate(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        rel = create_relation(a, b, "IMPLIES")
        assert deactivate_relation(rel.relation_id)
        rels = get_relations(a, direction="outgoing")
        assert len(rels) == 0

    def test_deactivate_nonexistent(self):
        assert deactivate_relation("nonexistent") is False


class TestGetNeighbors:
    def test_direct_neighbors(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(a, c, "SUPPORTS")
        neighbors = get_neighbors(a, max_depth=1)
        assert set(neighbors) == {b, c}

    def test_two_hop_neighbors(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(b, c, "IMPLIES")
        neighbors = get_neighbors(a, max_depth=2)
        assert set(neighbors) == {b, c}

    def test_depth_limit(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(b, c, "IMPLIES")
        neighbors = get_neighbors(a, max_depth=1)
        assert set(neighbors) == {b}

    def test_filter_by_type(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(a, c, "SUPPORTS")
        neighbors = get_neighbors(a, relation_type="IMPLIES", max_depth=1)
        assert neighbors == [b]

    def test_no_neighbors(self):
        a = _insert_knowledge()
        assert get_neighbors(a) == []


class TestInverseRelations:
    def test_all_types_have_inverses(self):
        for rtype in RELATION_TYPES:
            assert rtype in INVERSE_RELATIONS

    def test_contradicts_is_symmetric(self):
        assert INVERSE_RELATIONS["CONTRADICTS"] == "CONTRADICTS"

    def test_implies_requires_inverse(self):
        assert INVERSE_RELATIONS["IMPLIES"] == "REQUIRES"
        assert INVERSE_RELATIONS["REQUIRES"] == "IMPLIES"

    def test_generalizes_specializes_inverse(self):
        assert INVERSE_RELATIONS["GENERALIZES"] == "SPECIALIZES"
        assert INVERSE_RELATIONS["SPECIALIZES"] == "GENERALIZES"
