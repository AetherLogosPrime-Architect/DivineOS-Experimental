"""Tests for the unified knowledge edge system."""

import time
import uuid

import pytest

from divineos.core.knowledge import get_connection
from divineos.core.knowledge import compute_hash, init_knowledge_table
from divineos.core.knowledge.edges import (
    ALL_EDGE_TYPES,
    INVERSE_EDGES,
    LOGICAL_TYPES,
    SEMANTIC_TYPES,
    create_edge,
    deactivate_edge,
    get_edge_summary,
    get_edges,
    get_neighbors,
    init_edge_table,
    remove_edge,
)
from divineos.core.ledger import init_db


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()
    init_edge_table()
    yield


def _insert_knowledge(content="test"):
    kid = str(uuid.uuid4())
    conn = get_connection()
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


class TestCreateEdge:
    def test_semantic_edge(self):
        a = _insert_knowledge("cause")
        b = _insert_knowledge("effect")
        edge = create_edge(a, b, "CAUSED_BY")
        assert edge.edge_type == "CAUSED_BY"
        assert edge.layer == "semantic"

    def test_logical_edge(self):
        a = _insert_knowledge("premise")
        b = _insert_knowledge("conclusion")
        edge = create_edge(a, b, "IMPLIES", layer="logical")
        assert edge.edge_type == "IMPLIES"
        assert edge.layer == "logical"

    def test_default_layer_assignment(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        # IMPLIES defaults to logical
        edge = create_edge(a, b, "IMPLIES")
        assert edge.layer == "logical"

    def test_shared_type_default_layer(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        # SUPPORTS defaults to semantic
        edge = create_edge(a, b, "SUPPORTS")
        assert edge.layer == "semantic"

    def test_explicit_layer_override(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        # SUPPORTS can be logical if caller says so
        edge = create_edge(a, b, "SUPPORTS", layer="logical")
        assert edge.layer == "logical"

    def test_all_edge_types_accepted(self):
        for etype in ALL_EDGE_TYPES:
            a = _insert_knowledge(f"a-{etype}")
            b = _insert_knowledge(f"b-{etype}")
            edge = create_edge(a, b, etype)
            assert edge.edge_type == etype

    def test_invalid_type_raises(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        with pytest.raises(ValueError, match="Invalid edge type"):
            create_edge(a, b, "VIBES")

    def test_self_edge_raises(self):
        a = _insert_knowledge()
        with pytest.raises(ValueError, match="itself"):
            create_edge(a, a, "IMPLIES")

    def test_duplicate_returns_existing(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        e1 = create_edge(a, b, "IMPLIES")
        e2 = create_edge(a, b, "IMPLIES")
        assert e1.edge_id == e2.edge_id

    def test_different_types_not_duplicate(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        e1 = create_edge(a, b, "IMPLIES")
        e2 = create_edge(a, b, "SUPPORTS")
        assert e1.edge_id != e2.edge_id


class TestGetEdges:
    def test_filter_by_layer(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_edge(a, b, "CAUSED_BY")  # semantic
        create_edge(a, c, "IMPLIES", layer="logical")  # logical

        semantic = get_edges(a, layer="semantic")
        logical = get_edges(a, layer="logical")
        all_edges = get_edges(a)

        assert len(semantic) == 1
        assert len(logical) == 1
        assert len(all_edges) == 2

    def test_filter_by_direction(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        create_edge(a, b, "IMPLIES")

        outgoing = get_edges(a, direction="outgoing")
        incoming = get_edges(a, direction="incoming")
        assert len(outgoing) == 1
        assert len(incoming) == 0

    def test_filter_by_type(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_edge(a, b, "IMPLIES")
        create_edge(a, c, "SUPPORTS")

        implies_only = get_edges(a, edge_type="IMPLIES")
        assert len(implies_only) == 1

    def test_combined_filters(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_edge(a, b, "SUPPORTS", layer="semantic")
        create_edge(a, c, "SUPPORTS", layer="logical")

        result = get_edges(a, layer="logical", edge_type="SUPPORTS")
        assert len(result) == 1
        assert result[0].target_id == c


class TestDeactivateAndRemove:
    def test_deactivate(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        edge = create_edge(a, b, "IMPLIES")
        assert deactivate_edge(edge.edge_id)
        assert get_edges(a) == []

    def test_remove(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        edge = create_edge(a, b, "IMPLIES")
        assert remove_edge(edge.edge_id)
        assert get_edges(a) == []

    def test_deactivate_nonexistent(self):
        assert deactivate_edge("nonexistent") is False

    def test_remove_nonexistent(self):
        assert remove_edge("nonexistent") is False


class TestGetNeighbors:
    def test_direct_neighbors(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_edge(a, b, "IMPLIES", layer="logical")
        create_edge(a, c, "CAUSED_BY")
        neighbors = get_neighbors(a, max_depth=1)
        assert set(neighbors) == {b, c}

    def test_layer_filtered_neighbors(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_edge(a, b, "IMPLIES", layer="logical")
        create_edge(a, c, "CAUSED_BY")
        logical_neighbors = get_neighbors(a, layer="logical", max_depth=1)
        assert logical_neighbors == [b]


class TestEdgeSummary:
    def test_summary_format(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        create_edge(a, b, "IMPLIES", layer="logical")
        summary = get_edge_summary(a)
        assert "IMPLIES" in summary

    def test_empty_summary(self):
        a = _insert_knowledge()
        assert get_edge_summary(a) == ""


class TestTypeConstants:
    def test_semantic_and_logical_overlap(self):
        shared = SEMANTIC_TYPES & LOGICAL_TYPES
        assert "SUPPORTS" in shared
        assert "CONTRADICTS" in shared

    def test_all_types_is_union(self):
        assert ALL_EDGE_TYPES == SEMANTIC_TYPES | LOGICAL_TYPES

    def test_all_types_have_inverses(self):
        for etype in ALL_EDGE_TYPES:
            assert etype in INVERSE_EDGES
