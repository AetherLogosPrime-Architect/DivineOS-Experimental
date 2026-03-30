"""Tests for knowledge graph export — mermaid and JSON formats."""

import json

import pytest

import divineos.core.ledger as ledger_mod
from divineos.core.knowledge import init_knowledge_table, store_knowledge
from divineos.core.knowledge.edges import (
    create_edge,
    graph_export,
    init_edge_table,
)
from divineos.core.ledger import init_db


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setattr(ledger_mod, "DB_PATH", test_db)
    monkeypatch.setattr(ledger_mod, "_get_db_path", lambda: test_db)
    init_db()
    init_knowledge_table()
    init_edge_table()
    yield


def _store(content: str, ktype: str = "FACT") -> str:
    return store_knowledge(ktype, content, confidence=0.9)


class TestMermaidExport:
    def test_empty_graph(self):
        result = graph_export(fmt="mermaid")
        assert result.startswith("graph LR")

    def test_basic_graph(self):
        a = _store("SQLite is embedded", "FACT")
        b = _store("Use SQLite for storage", "PRINCIPLE")
        create_edge(a, b, "SUPPORTS")

        result = graph_export(fmt="mermaid")
        assert "graph LR" in result
        assert a[:8] in result
        assert b[:8] in result
        assert "SUPPORTS" in result

    def test_node_shapes_by_type(self):
        a = _store("Always test first", "FACT")
        b = _store("Never delete data", "BOUNDARY")
        create_edge(a, b, "RELATED_TO")

        result = graph_export(fmt="mermaid")
        # FACT uses ["..."], BOUNDARY uses {{"..."}}
        assert a[:8] + '["' in result
        assert b[:8] + '{{"' in result

    def test_style_classes(self):
        a = _store("Test fact", "FACT")
        b = _store("Test boundary", "BOUNDARY")
        create_edge(a, b, "SUPPORTS")

        result = graph_export(fmt="mermaid")
        assert "classDef fact" in result
        assert "classDef boundary" in result


class TestJsonExport:
    def test_empty_graph(self):
        result = graph_export(fmt="json")
        data = json.loads(result)
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_basic_graph(self):
        a = _store("Knowledge A")
        b = _store("Knowledge B")
        create_edge(a, b, "CAUSED_BY")

        result = graph_export(fmt="json")
        data = json.loads(result)
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

        edge = data["edges"][0]
        assert edge["source"] == a
        assert edge["target"] == b
        assert edge["type"] == "CAUSED_BY"

    def test_node_metadata(self):
        kid = _store("SQLite is reliable", "FACT")
        kid2 = _store("Another fact")
        create_edge(kid, kid2, "SUPPORTS")

        result = graph_export(fmt="json")
        data = json.loads(result)
        node = next(n for n in data["nodes"] if n["id"] == kid)
        assert node["type"] == "FACT"
        assert "SQLite" in node["label"]
        assert node["confidence"] == 0.9


class TestCenteredExport:
    def test_centered_limits_depth(self):
        a = _store("Node A")
        b = _store("Node B")
        c = _store("Node C")
        d = _store("Node D")
        create_edge(a, b, "SUPPORTS")
        create_edge(b, c, "SUPPORTS")
        create_edge(c, d, "SUPPORTS")

        # Center on B with depth 1 — should get A, B, C but NOT D
        result = graph_export(center_id=b, depth=1, fmt="json")
        data = json.loads(result)
        node_ids = {n["id"] for n in data["nodes"]}
        assert a in node_ids
        assert b in node_ids
        assert c in node_ids
        assert d not in node_ids
