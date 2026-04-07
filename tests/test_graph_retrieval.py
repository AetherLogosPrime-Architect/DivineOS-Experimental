"""Tests for Graph-Enhanced Retrieval — knowledge as clusters."""

import os

from divineos.core.knowledge._base import (
    init_knowledge_table,
)
from divineos.core.knowledge.crud import (
    store_knowledge,
)
from divineos.core.knowledge.edges import (
    create_edge,
    init_edge_table,
)
from divineos.core.knowledge.graph_retrieval import (
    build_knowledge_cluster,
    cluster_for_briefing,
    format_cluster_line,
    get_graph_connections_for_recall,
)
from divineos.core.ledger import init_db


def _setup_db(tmp_path):
    """Initialize test database."""
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    init_db()
    init_knowledge_table()
    init_edge_table()


def _cleanup():
    os.environ.pop("DIVINEOS_DB", None)


class TestBuildKnowledgeCluster:
    """Cluster building from a seed entry."""

    def test_cluster_with_connections(self, tmp_path):
        _setup_db(tmp_path)
        try:
            kid1 = store_knowledge("PRINCIPLE", "Always read before editing", 0.9)
            kid2 = store_knowledge("OBSERVATION", "Blind edits cause rework", 0.8)
            create_edge(kid1, kid2, "SUPPORTS")

            cluster = build_knowledge_cluster(kid1)
            assert cluster["seed"] is not None
            assert cluster["seed"]["knowledge_id"] == kid1
            assert len(cluster["connections"]) == 1
            assert cluster["connections"][0]["entry"]["knowledge_id"] == kid2
            assert cluster["connections"][0]["edge_type"] == "SUPPORTS"
        finally:
            _cleanup()

    def test_cluster_no_connections(self, tmp_path):
        _setup_db(tmp_path)
        try:
            kid = store_knowledge("FACT", "Isolated fact", 0.7)
            cluster = build_knowledge_cluster(kid)
            assert cluster["seed"] is not None
            assert len(cluster["connections"]) == 0
        finally:
            _cleanup()

    def test_cluster_nonexistent_entry(self, tmp_path):
        _setup_db(tmp_path)
        try:
            cluster = build_knowledge_cluster("nonexistent")
            assert cluster["seed"] is None
        finally:
            _cleanup()

    def test_cluster_respects_max_neighbors(self, tmp_path):
        _setup_db(tmp_path)
        try:
            seed = store_knowledge("PRINCIPLE", "Central principle", 0.9)
            for i in range(10):
                kid = store_knowledge("OBSERVATION", f"Observation {i}", 0.7)
                create_edge(seed, kid, "SUPPORTS")

            cluster = build_knowledge_cluster(seed, max_neighbors=3)
            assert len(cluster["connections"]) == 3
        finally:
            _cleanup()

    def test_cluster_skips_superseded(self, tmp_path):
        _setup_db(tmp_path)
        try:
            from divineos.core.knowledge.crud import supersede_knowledge

            kid1 = store_knowledge("PRINCIPLE", "Active principle", 0.9)
            kid2 = store_knowledge("FACT", "Old fact", 0.7)
            create_edge(kid1, kid2, "RELATED_TO")
            supersede_knowledge(kid2, "outdated")

            cluster = build_knowledge_cluster(kid1)
            assert len(cluster["connections"]) == 0
        finally:
            _cleanup()


class TestClusterForBriefing:
    """Grouping briefing entries by graph connections."""

    def test_connected_entries_clustered(self, tmp_path):
        _setup_db(tmp_path)
        try:
            kid1 = store_knowledge("PRINCIPLE", "Read before edit", 0.9)
            kid2 = store_knowledge("OBSERVATION", "Blind edits fail", 0.8)
            kid3 = store_knowledge("FACT", "Unrelated fact", 0.7)
            create_edge(kid1, kid2, "SUPPORTS")

            entries = [
                {"knowledge_id": kid1, "content": "Read before edit", "confidence": 0.9},
                {"knowledge_id": kid2, "content": "Blind edits fail", "confidence": 0.8},
                {"knowledge_id": kid3, "content": "Unrelated fact", "confidence": 0.7},
            ]
            clusters = cluster_for_briefing(entries)

            # Should have a cluster (kid1+kid2) and a standalone (kid3)
            non_standalone = [c for c in clusters if not c["standalone"]]
            standalone = [c for c in clusters if c["standalone"]]
            assert len(non_standalone) >= 1
            assert len(standalone) >= 1
        finally:
            _cleanup()

    def test_no_edges_all_standalone(self, tmp_path):
        _setup_db(tmp_path)
        try:
            kid1 = store_knowledge("FACT", "Fact 1", 0.7)
            kid2 = store_knowledge("FACT", "Fact 2", 0.7)

            entries = [
                {"knowledge_id": kid1, "content": "Fact 1", "confidence": 0.7},
                {"knowledge_id": kid2, "content": "Fact 2", "confidence": 0.7},
            ]
            clusters = cluster_for_briefing(entries)
            assert all(c["standalone"] for c in clusters)
        finally:
            _cleanup()

    def test_respects_max_clusters(self, tmp_path):
        _setup_db(tmp_path)
        try:
            entries = []
            prev_kid = None
            for i in range(10):
                kid = store_knowledge("FACT", f"Chained fact {i}", 0.7)
                entries.append(
                    {"knowledge_id": kid, "content": f"Chained fact {i}", "confidence": 0.7}
                )
                if prev_kid:
                    create_edge(prev_kid, kid, "RELATED_TO")
                prev_kid = kid

            clusters = cluster_for_briefing(entries, max_clusters=2)
            non_standalone = [c for c in clusters if not c["standalone"]]
            assert len(non_standalone) <= 2
        finally:
            _cleanup()

    def test_empty_entries(self, tmp_path):
        _setup_db(tmp_path)
        try:
            clusters = cluster_for_briefing([])
            assert clusters == []
        finally:
            _cleanup()


class TestFormatClusterLine:
    """Formatting individual connection lines."""

    def test_outgoing_format(self):
        connection = {
            "entry": {"content": "Blind edits cause rework", "confidence": 0.8},
            "edge_type": "SUPPORTS",
            "direction": "outgoing",
        }
        line = format_cluster_line(connection)
        assert "->" in line
        assert "supports" in line
        assert "0.80" in line
        assert "Blind edits" in line

    def test_incoming_format(self):
        connection = {
            "entry": {"content": "Read before editing", "confidence": 0.9},
            "edge_type": "CAUSED_BY",
            "direction": "incoming",
        }
        line = format_cluster_line(connection)
        assert "<-" in line
        assert "caused by" in line

    def test_truncates_long_content(self):
        connection = {
            "entry": {"content": "A" * 200, "confidence": 0.5},
            "edge_type": "RELATED_TO",
            "direction": "outgoing",
        }
        line = format_cluster_line(connection)
        assert "..." in line
        assert len(line) < 200


class TestGraphConnectionsForRecall:
    """Finding graph-connected entries for the recall function."""

    def test_finds_connected_entries(self, tmp_path):
        _setup_db(tmp_path)
        try:
            kid1 = store_knowledge("PRINCIPLE", "Main principle", 0.9)
            kid2 = store_knowledge("OBSERVATION", "Supporting observation", 0.8)
            create_edge(kid1, kid2, "SUPPORTS")

            active = [{"knowledge_id": kid1, "content": "Main principle"}]
            connections = get_graph_connections_for_recall(active)

            assert len(connections) >= 1
            assert connections[0]["entry"]["knowledge_id"] == kid2
            assert connections[0]["edge_type"] == "SUPPORTS"
            assert connections[0]["via"] == kid1
        finally:
            _cleanup()

    def test_skips_already_active(self, tmp_path):
        _setup_db(tmp_path)
        try:
            kid1 = store_knowledge("PRINCIPLE", "Principle A", 0.9)
            kid2 = store_knowledge("PRINCIPLE", "Principle B", 0.9)
            create_edge(kid1, kid2, "RELATED_TO")

            # Both already in active — should find nothing new
            active = [
                {"knowledge_id": kid1, "content": "A"},
                {"knowledge_id": kid2, "content": "B"},
            ]
            connections = get_graph_connections_for_recall(active)
            assert len(connections) == 0
        finally:
            _cleanup()

    def test_skips_low_confidence(self, tmp_path):
        _setup_db(tmp_path)
        try:
            kid1 = store_knowledge("PRINCIPLE", "Good principle", 0.9)
            kid2 = store_knowledge("OBSERVATION", "Weak observation", 0.1)
            create_edge(kid1, kid2, "SUPPORTS")

            active = [{"knowledge_id": kid1, "content": "Good principle"}]
            connections = get_graph_connections_for_recall(active)
            assert len(connections) == 0  # kid2 confidence too low
        finally:
            _cleanup()

    def test_respects_max_connections(self, tmp_path):
        _setup_db(tmp_path)
        try:
            seed = store_knowledge("PRINCIPLE", "Central", 0.9)
            for i in range(20):
                kid = store_knowledge("FACT", f"Fact {i}", 0.7)
                create_edge(seed, kid, "SUPPORTS")

            active = [{"knowledge_id": seed, "content": "Central"}]
            connections = get_graph_connections_for_recall(active, max_connections=5)
            assert len(connections) <= 5
        finally:
            _cleanup()

    def test_empty_active_returns_empty(self, tmp_path):
        _setup_db(tmp_path)
        try:
            connections = get_graph_connections_for_recall([])
            assert connections == []
        finally:
            _cleanup()


class TestEdgesBatch:
    """Batch edge loading for performance."""

    def test_batch_returns_all_edges(self, tmp_path):
        from divineos.core.knowledge.edges import get_edges_batch

        _setup_db(tmp_path)
        try:
            k1 = store_knowledge("PRINCIPLE", "Principle one", 0.9)
            k2 = store_knowledge("OBSERVATION", "Observation two", 0.8)
            k3 = store_knowledge("FACT", "Fact three", 0.7)
            create_edge(k1, k2, "SUPPORTS")
            create_edge(k2, k3, "ELABORATES")

            result = get_edges_batch({k1, k2, k3}, layer="semantic")
            assert k1 in result
            assert k2 in result
            assert len(result[k1]) >= 1  # k1->k2
            assert len(result[k2]) >= 1  # k2 connected to both
        finally:
            _cleanup()

    def test_batch_empty_input(self, tmp_path):
        from divineos.core.knowledge.edges import get_edges_batch

        _setup_db(tmp_path)
        try:
            result = get_edges_batch(set())
            assert result == {}
        finally:
            _cleanup()

    def test_batch_no_edges(self, tmp_path):
        from divineos.core.knowledge.edges import get_edges_batch

        _setup_db(tmp_path)
        try:
            k1 = store_knowledge("FACT", "Isolated fact", 0.7)
            result = get_edges_batch({k1})
            assert result[k1] == []
        finally:
            _cleanup()
