"""Tests that recall() and ask actually TRAVERSE the knowledge graph.

The load-bearing property (exploration/aether/88): get_graph_connections_for_
recall was built and never called — sleep strengthened edges nightly but only
briefing clusters traversed them, so the edges were wallpaper for the retrieval
actually used (ask/recall). These tests pin the WIRING, not the graph function
itself (that is covered in test_graph_retrieval.py): they fail if recall stops
returning the ``connected`` key or if the spreader is unwired again.
"""

from __future__ import annotations

import os

from divineos.core import active_memory
from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge.crud import store_knowledge
from divineos.core.knowledge.edges import create_edge, init_edge_table
from divineos.core.ledger import init_db
from divineos.core.memory import init_memory_tables


def _setup_db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    init_db()
    init_knowledge_table()
    init_edge_table()
    init_memory_tables()


def _cleanup():
    os.environ.pop("DIVINEOS_DB", None)


def test_recall_returns_connected_key(tmp_path):
    _setup_db(tmp_path)
    try:
        result = active_memory.recall()
        # The key exists unconditionally — the wiring is present even when
        # there are no edges to traverse.
        assert "connected" in result
        assert isinstance(result["connected"], list)
    finally:
        _cleanup()


def test_recall_traverses_edge_to_neighbor(tmp_path, monkeypatch):
    _setup_db(tmp_path)
    try:
        seed = store_knowledge("PRINCIPLE", "Always read before editing", 0.9)
        neighbor = store_knowledge("OBSERVATION", "Blind edits cause rework", 0.8)
        create_edge(seed, neighbor, "SUPPORTS")

        # Force the active set to contain the seed so the spreader has a
        # starting point (bypasses the active-memory promotion pipeline).
        seed_entry = {
            "knowledge_id": seed,
            "content": "Always read before editing",
            "confidence": 0.9,
            "importance": 1.0,
        }
        monkeypatch.setattr(active_memory, "get_active_memory", lambda: [seed_entry])

        result = active_memory.recall()
        connected_ids = {c["entry"]["knowledge_id"] for c in result["connected"]}
        assert neighbor in connected_ids  # the edge was actually traversed
    finally:
        _cleanup()


def test_recall_connected_empty_when_no_edges(tmp_path, monkeypatch):
    _setup_db(tmp_path)
    try:
        lonely = store_knowledge("FACT", "Isolated fact with no edges", 0.7)
        seed_entry = {
            "knowledge_id": lonely,
            "content": "Isolated fact with no edges",
            "confidence": 0.7,
            "importance": 1.0,
        }
        monkeypatch.setattr(active_memory, "get_active_memory", lambda: [seed_entry])

        result = active_memory.recall()
        assert result["connected"] == []  # no edges -> nothing pulled in
    finally:
        _cleanup()
