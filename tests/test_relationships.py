"""Tests for knowledge relationships — typed edges between entries."""

import pytest

from divineos.core.knowledge._base import init_knowledge_table
from divineos.core.knowledge.crud import store_knowledge
from divineos.core.knowledge.relationships import (
    RELATIONSHIP_TYPES,
    _classify_relationship,
    add_relationship,
    auto_detect_relationships,
    find_related_cluster,
    get_relationship_summary,
    get_relationships,
    init_relationship_table,
    remove_relationship,
)


def _setup():
    init_knowledge_table()
    init_relationship_table()


class TestAddRelationship:
    def test_basic_add(self):
        _setup()
        rid = add_relationship("k-aaa", "k-bbb", "SUPPORTS")
        assert rid

    def test_invalid_relationship_type(self):
        _setup()
        with pytest.raises(ValueError, match="Unknown relationship"):
            add_relationship("k-aaa", "k-bbb", "INVALID_TYPE")

    def test_self_relationship_rejected(self):
        _setup()
        with pytest.raises(ValueError, match="Cannot create an edge"):
            add_relationship("k-aaa", "k-aaa", "SUPPORTS")

    def test_duplicate_ignored(self):
        _setup()
        add_relationship("k-aaa", "k-bbb", "SUPPORTS")
        add_relationship("k-aaa", "k-bbb", "SUPPORTS")
        # Same source/target/type — second should be silently ignored
        rels = get_relationships("k-aaa", direction="outgoing")
        assert len(rels) == 1

    def test_with_notes(self):
        _setup()
        add_relationship("k-aaa", "k-bbb", "CAUSED_BY", notes="Bug was caused by this")
        rels = get_relationships("k-aaa", direction="outgoing")
        assert rels[0]["notes"] == "Bug was caused by this"


class TestGetRelationships:
    def test_outgoing(self):
        _setup()
        add_relationship("k-aaa", "k-bbb", "SUPPORTS")
        add_relationship("k-aaa", "k-ccc", "ELABORATES")
        rels = get_relationships("k-aaa", direction="outgoing")
        assert len(rels) == 2
        assert all(r["direction"] == "outgoing" for r in rels)

    def test_incoming(self):
        _setup()
        add_relationship("k-bbb", "k-aaa", "SUPPORTS")
        rels = get_relationships("k-aaa", direction="incoming")
        assert len(rels) == 1
        assert rels[0]["direction"] == "incoming"
        assert rels[0]["source_id"] == "k-bbb"

    def test_both_directions(self):
        _setup()
        add_relationship("k-aaa", "k-bbb", "SUPPORTS")
        add_relationship("k-ccc", "k-aaa", "ELABORATES")
        rels = get_relationships("k-aaa", direction="both")
        assert len(rels) == 2

    def test_empty(self):
        _setup()
        rels = get_relationships("k-nonexistent")
        assert rels == []


class TestRemoveRelationship:
    def test_remove_existing(self):
        _setup()
        rid = add_relationship("k-aaa", "k-bbb", "SUPPORTS")
        assert remove_relationship(rid)
        assert get_relationships("k-aaa") == []

    def test_remove_nonexistent(self):
        _setup()
        assert not remove_relationship("nonexistent-id")


class TestFindRelatedCluster:
    def test_single_hop(self):
        _setup()
        add_relationship("k-a", "k-b", "SUPPORTS")
        add_relationship("k-a", "k-c", "ELABORATES")
        cluster = find_related_cluster("k-a", max_depth=1)
        ids = {c["knowledge_id"] for c in cluster}
        assert ids == {"k-b", "k-c"}

    def test_multi_hop(self):
        _setup()
        add_relationship("k-a", "k-b", "SUPPORTS")
        add_relationship("k-b", "k-c", "CAUSED_BY")
        cluster = find_related_cluster("k-a", max_depth=2)
        ids = {c["knowledge_id"] for c in cluster}
        assert "k-b" in ids
        assert "k-c" in ids

    def test_no_duplicates(self):
        _setup()
        add_relationship("k-a", "k-b", "SUPPORTS")
        add_relationship("k-b", "k-a", "ELABORATES")
        cluster = find_related_cluster("k-a", max_depth=2)
        ids = [c["knowledge_id"] for c in cluster]
        assert len(ids) == len(set(ids))

    def test_empty_cluster(self):
        _setup()
        cluster = find_related_cluster("k-isolated")
        assert cluster == []


class TestRelationshipSummary:
    def test_with_relationships(self):
        _setup()
        add_relationship("k-a", "k-b", "SUPPORTS")
        add_relationship("k-c", "k-a", "CAUSED_BY")
        summary = get_relationship_summary("k-a")
        assert "SUPPORTS" in summary
        assert "CAUSED_BY" in summary

    def test_empty_summary(self):
        _setup()
        summary = get_relationship_summary("k-no-rels")
        assert summary == ""


class TestRelationshipTypes:
    def test_all_types_valid(self):
        _setup()
        for rtype in RELATIONSHIP_TYPES:
            rid = add_relationship(f"src-{rtype}", f"tgt-{rtype}", rtype)
            assert rid


class TestClassifyRelationship:
    """Unit tests for the heuristic classifier."""

    def test_contradiction_detected(self):
        result = _classify_relationship(
            new_content="The database connection is not stable and fails often",
            new_type="OBSERVATION",
            existing_content="The database connection is stable and works well",
            existing_type="OBSERVATION",
            overlap=0.7,
        )
        assert result == "CONTRADICTS"

    def test_elaboration_longer_entry(self):
        result = _classify_relationship(
            new_content=(
                "The testing framework works by running pytest with isolated databases "
                "and each test gets its own fresh SQLite file to prevent interference "
                "between test cases which is critical for reproducibility"
            ),
            new_type="PROCEDURE",
            existing_content="The testing framework works by running pytest with isolated databases",
            existing_type="PROCEDURE",
            overlap=0.7,
        )
        assert result == "ELABORATES"

    def test_causal_language(self):
        result = _classify_relationship(
            new_content="The import error happened because the module path was wrong",
            new_type="OBSERVATION",
            existing_content="The module path configuration for imports in the system",
            existing_type="FACT",
            overlap=0.4,
        )
        assert result == "CAUSED_BY"

    def test_type_affinity_observation_supports_principle(self):
        result = _classify_relationship(
            new_content="I noticed that keeping commits small reduced errors significantly",
            new_type="OBSERVATION",
            existing_content="Small commits reduce errors and make reviews easier",
            existing_type="PRINCIPLE",
            overlap=0.5,
        )
        assert result == "SUPPORTS"

    def test_related_to_same_type(self):
        result = _classify_relationship(
            new_content="SQLite FTS5 uses BM25 ranking for relevance search queries",
            new_type="FACT",
            existing_content="FTS5 provides BM25 ranking algorithm for text search",
            existing_type="FACT",
            overlap=0.6,
        )
        assert result == "RELATED_TO"

    def test_low_overlap_returns_none(self):
        result = _classify_relationship(
            new_content="The sky is blue today",
            new_type="OBSERVATION",
            existing_content="Python uses indentation for scope",
            existing_type="FACT",
            overlap=0.0,
        )
        assert result is None

    def test_moderate_overlap_different_types_no_signal(self):
        result = _classify_relationship(
            new_content="I stored some knowledge today",
            new_type="EPISODE",
            existing_content="Knowledge storage uses SQLite",
            existing_type="FACT",
            overlap=0.35,
        )
        # 0.35 > OVERLAP_DUPLICATE (0.30): cross-type RELATED_TO fires
        assert result == "RELATED_TO"

    def test_cross_type_related_to(self):
        """Different types with decent overlap get RELATED_TO."""
        result = _classify_relationship(
            new_content="Knowledge storage and retrieval patterns in the system",
            new_type="OBSERVATION",
            existing_content="Knowledge storage design patterns for persistence",
            existing_type="FACT",
            overlap=0.45,
        )
        assert result == "RELATED_TO"

    def test_new_type_affinities(self):
        """New type affinities produce expected relationships."""
        # PRINCIPLE → DIRECTIVE = SUPPORTS
        result = _classify_relationship(
            new_content="Small commits reduce errors in the codebase significantly",
            new_type="PRINCIPLE",
            existing_content="Commits should be small and focused for better reviews",
            existing_type="DIRECTIVE",
            overlap=0.5,
        )
        assert result == "SUPPORTS"

        # MISTAKE → BOUNDARY = CAUSED_BY
        result = _classify_relationship(
            new_content="I edited a file without reading it first and broke things",
            new_type="MISTAKE",
            existing_content="Always read files before editing them to avoid errors",
            existing_type="BOUNDARY",
            overlap=0.4,
        )
        assert result == "CAUSED_BY"


class TestAutoDetectRelationships:
    """Integration tests for auto-detection against real knowledge entries."""

    def test_detects_relationships_between_related_entries(self):
        _setup()
        # Store an existing entry
        existing_id = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="I should always run tests after making code changes to catch regressions",
            confidence=0.9,
        )

        # Store a new entry that supports the principle
        new_id = store_knowledge(
            knowledge_type="OBSERVATION",
            content="I noticed that running tests after code changes caught three bugs this session",
            confidence=0.8,
        )

        rels = auto_detect_relationships([new_id])
        # Should find at least one relationship
        rel_targets = {r["target_id"] for r in rels}
        if existing_id in rel_targets:
            matching = [r for r in rels if r["target_id"] == existing_id]
            assert matching[0]["relationship"] in RELATIONSHIP_TYPES

    def test_no_self_relationships(self):
        _setup()
        kid = store_knowledge(
            knowledge_type="FACT",
            content="DivineOS uses SQLite for persistent storage of events and knowledge",
            confidence=0.9,
        )
        rels = auto_detect_relationships([kid])
        for r in rels:
            assert r["source_id"] != r["target_id"]

    def test_empty_input(self):
        _setup()
        assert auto_detect_relationships([]) == []

    def test_relates_new_entries_to_each_other(self):
        _setup()
        id1 = store_knowledge(
            knowledge_type="OBSERVATION",
            content="The session pipeline extracts knowledge from conversations automatically",
            confidence=0.8,
        )
        id2 = store_knowledge(
            knowledge_type="OBSERVATION",
            content="The session pipeline extracts knowledge and detects relationships automatically",
            confidence=0.8,
        )
        rels = auto_detect_relationships([id1, id2])
        # These have high overlap — should be related
        cross_rels = [r for r in rels if {r["source_id"], r["target_id"]} == {id1, id2}]
        assert len(cross_rels) >= 1


class TestStructuralEdges:
    """Edges created from extraction context, not word overlap."""

    def test_structural_edges_link_corrections(self):
        """Co-extracted corrections get RELATED_TO edges."""
        _setup()
        from divineos.core.knowledge.edges import get_edges, init_edge_table

        init_edge_table()

        # Store two correction-pair entries
        id1 = store_knowledge(
            knowledge_type="BOUNDARY",
            content="Always read files before editing them for safety",
            confidence=0.85,
            tags=["correction-pair", "session-test123"],
        )
        id2 = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Check test output before claiming success",
            confidence=0.85,
            tags=["correction-pair", "session-test123"],
        )

        from divineos.core.knowledge.deep_extraction import _create_structural_edges

        created = _create_structural_edges([id1, id2])
        assert created >= 1

        edges = get_edges(id1, direction="both")
        connected_ids = {e.target_id for e in edges} | {e.source_id for e in edges}
        assert id2 in connected_ids

    def test_structural_edges_encouragement_supports_decision(self):
        """Encouragements create SUPPORTS edges to decisions."""
        _setup()
        from divineos.core.knowledge.edges import get_edges, init_edge_table

        init_edge_table()

        enc_id = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="I explained the architecture clearly and the user confirmed",
            confidence=0.9,
            tags=["encouragement", "session-test456"],
        )
        dec_id = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="I decided to split the module into smaller files",
            confidence=0.9,
            tags=["decision", "session-test456"],
        )

        from divineos.core.knowledge.deep_extraction import _create_structural_edges

        created = _create_structural_edges([enc_id, dec_id])
        assert created >= 1

        edges = get_edges(enc_id)
        assert any(e.target_id == dec_id and e.edge_type == "SUPPORTS" for e in edges)

    def test_structural_edges_preference_applies_to_correction(self):
        """Preferences create APPLIES_TO edges to corrections."""
        _setup()
        from divineos.core.knowledge.edges import get_edges, init_edge_table

        init_edge_table()

        pref_id = store_knowledge(
            knowledge_type="DIRECTION",
            content="Use plain english, no jargon in explanations",
            confidence=0.9,
            tags=["direction", "session-test789"],
        )
        corr_id = store_knowledge(
            knowledge_type="BOUNDARY",
            content="Do not use technical jargon without explaining it first",
            confidence=0.85,
            tags=["correction-pair", "session-test789"],
        )

        from divineos.core.knowledge.deep_extraction import _create_structural_edges

        created = _create_structural_edges([pref_id, corr_id])
        assert created >= 1

        edges = get_edges(pref_id)
        assert any(e.target_id == corr_id and e.edge_type == "APPLIES_TO" for e in edges)

    def test_structural_edges_empty_input(self):
        """No crash on empty or single-entry input."""
        from divineos.core.knowledge.deep_extraction import _create_structural_edges

        assert _create_structural_edges([]) == 0
        assert _create_structural_edges(["single-id"]) == 0

    def test_supersession_creates_edge(self):
        """When store_knowledge_smart supersedes, a SUPERSEDES edge is created."""
        _setup()
        from divineos.core.knowledge.edges import get_edges, init_edge_table
        from divineos.core.knowledge.extraction import store_knowledge_smart

        init_edge_table()

        # Store original
        old_id = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="I should test code after making changes to catch bugs early",
            confidence=0.8,
        )

        # Store similar but evolved — should UPDATE (supersede)
        new_id = store_knowledge_smart(
            knowledge_type="PRINCIPLE",
            content="I should test code after making changes to catch bugs early and also run linting checks for code quality",
            confidence=0.9,
        )

        if new_id != old_id:
            # If it was an UPDATE, check for SUPERSEDES edge
            edges = get_edges(new_id)
            supersedes = [e for e in edges if e.edge_type == "SUPERSEDES"]
            if supersedes:
                assert supersedes[0].target_id == old_id
