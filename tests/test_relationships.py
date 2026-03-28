"""Tests for knowledge relationships — typed edges between entries."""

import pytest

from divineos.core.knowledge._base import init_knowledge_table
from divineos.core.knowledge.relationships import (
    RELATIONSHIP_TYPES,
    add_relationship,
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
        with pytest.raises(ValueError, match="Cannot relate"):
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
