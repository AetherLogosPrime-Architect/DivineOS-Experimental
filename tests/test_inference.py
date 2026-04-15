"""Tests for the forward-chaining inference engine."""

import time
import uuid

import pytest

from divineos.core.knowledge import _get_connection, compute_hash, init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.logic.logic_reasoning import (
    Derivation,
    create_inference_warrants,
    create_relation,
    forward_chain,
    init_relation_table,
    propagate_from,
)
from divineos.core.logic.warrants import get_warrants, init_warrant_table


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


class TestForwardChain:
    def test_no_implies_edges(self):
        a = _insert_knowledge()
        assert forward_chain(a) == []

    def test_single_hop(self):
        a = _insert_knowledge("premise")
        b = _insert_knowledge("conclusion")
        create_relation(a, b, "IMPLIES")
        derivations = forward_chain(a)
        assert len(derivations) == 1
        assert derivations[0].target_id == b
        assert derivations[0].depth == 1

    def test_two_hop_chain(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(b, c, "IMPLIES")
        derivations = forward_chain(a)
        assert len(derivations) == 2
        targets = {d.target_id for d in derivations}
        assert targets == {b, c}

    def test_confidence_decays_with_depth(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES", confidence=1.0)
        create_relation(b, c, "IMPLIES", confidence=1.0)
        derivations = forward_chain(a)
        by_target = {d.target_id: d for d in derivations}
        assert by_target[b].confidence > by_target[c].confidence

    def test_min_confidence_cutoff(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        create_relation(a, b, "IMPLIES", confidence=0.2)
        # With decay, 0.2 * 0.85 = 0.17, below default MIN_INFERENCE_CONFIDENCE
        derivations = forward_chain(a, min_confidence=0.3)
        assert len(derivations) == 0

    def test_max_depth_limit(self):
        nodes = [_insert_knowledge(f"n{i}") for i in range(5)]
        for i in range(len(nodes) - 1):
            create_relation(nodes[i], nodes[i + 1], "IMPLIES")
        derivations = forward_chain(nodes[0], max_depth=2)
        targets = {d.target_id for d in derivations}
        assert nodes[1] in targets
        assert nodes[2] in targets
        assert nodes[3] not in targets

    def test_branching_graph(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(a, c, "IMPLIES")
        derivations = forward_chain(a)
        assert len(derivations) == 2

    def test_no_cycles(self):
        """Graph with cycle should not loop forever."""
        a = _insert_knowledge()
        b = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(b, a, "IMPLIES")
        derivations = forward_chain(a)
        # Should find b but not loop back to a
        assert len(derivations) == 1
        assert derivations[0].target_id == b

    def test_only_follows_implies(self):
        """SUPPORTS and other types are not followed."""
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(a, c, "SUPPORTS")
        derivations = forward_chain(a)
        assert len(derivations) == 1
        assert derivations[0].target_id == b


class TestCreateInferenceWarrants:
    def test_creates_warrants(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        derivations = forward_chain(a)
        count = create_inference_warrants(a, derivations, source_session="sess-1")
        assert count == 1
        warrants = get_warrants(b, status="ACTIVE")
        assert any(w.warrant_type == "INFERENTIAL" for w in warrants)

    def test_no_duplicate_warrants(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        derivations = forward_chain(a)
        create_inference_warrants(a, derivations)
        count = create_inference_warrants(a, derivations)
        assert count == 0  # already exists

    def test_backing_ids_recorded(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        derivations = forward_chain(a)
        create_inference_warrants(a, derivations)
        warrants = get_warrants(b, status="ACTIVE")
        inferential = [w for w in warrants if w.warrant_type == "INFERENTIAL"]
        assert len(inferential) == 1
        assert a in inferential[0].backing_ids


class TestPropagateFrom:
    def test_propagate_full_pass(self):
        a = _insert_knowledge()
        b = _insert_knowledge()
        c = _insert_knowledge()
        create_relation(a, b, "IMPLIES")
        create_relation(b, c, "IMPLIES")
        derivations = propagate_from(a, source_session="sess-1")
        assert len(derivations) == 2

    def test_propagate_no_edges(self):
        a = _insert_knowledge()
        derivations = propagate_from(a)
        assert derivations == []


class TestDerivationDataclass:
    def test_depth_property(self):
        d = Derivation(target_id="t", source_chain=["a", "b", "t"], confidence=0.7)
        assert d.depth == 2

    def test_single_hop_depth(self):
        d = Derivation(target_id="t", source_chain=["a", "t"], confidence=0.85)
        assert d.depth == 1
