"""Tests for the Hebbian edge-strengthening function (prereg-e36b567a6959).

When sleep recombination re-discovers an existing knowledge edge,
its confidence gets bumped by HEBBIAN_STRENGTHEN_DELTA. Edges proven
by repeated structural similarity accumulate evidence weight; one-time
matches stay at their initial confidence.

This test file covers the strengthen_edge function in isolation. The
sleep-cycle integration is tested by the existing sleep tests via the
SleepReport.connections_strengthened counter.
"""

import time
import uuid

from divineos.core.knowledge import compute_hash, init_knowledge_table
from divineos.core.knowledge._base import _get_connection
from divineos.core.knowledge.edges import (
    HEBBIAN_STRENGTHEN_DELTA,
    create_edge,
    find_edge,
    init_edge_table,
    strengthen_edge,
)
from divineos.core.ledger import init_db


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()
    init_edge_table()


def _make_knowledge(content: str) -> str:
    """Insert a minimal knowledge entry and return its id."""
    kid = str(uuid.uuid4())
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO knowledge
               (knowledge_id, created_at, updated_at, knowledge_type, content,
                confidence, source_events, tags, access_count, content_hash)
               VALUES (?, ?, ?, ?, ?, 1.0, '[]', '[]', 0, ?)""",
            (
                kid,
                time.time(),
                time.time(),
                "PRINCIPLE",
                content,
                compute_hash(content),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return kid


class TestHebbianStrengthening:
    def test_bumps_confidence_by_delta(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        a = _make_knowledge("entry a")
        b = _make_knowledge("entry b")
        edge = create_edge(a, b, "RELATED_TO", confidence=0.5)
        new_conf = strengthen_edge(edge.edge_id)
        assert new_conf is not None
        assert abs(new_conf - (0.5 + HEBBIAN_STRENGTHEN_DELTA)) < 1e-9

    def test_caps_at_one(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        a = _make_knowledge("entry a")
        b = _make_knowledge("entry b")
        edge = create_edge(a, b, "RELATED_TO", confidence=0.99)
        new_conf = strengthen_edge(edge.edge_id, delta=0.5)
        assert new_conf == 1.0

    def test_returns_none_for_missing_edge(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        result = strengthen_edge("nonexistent-edge-id")
        assert result is None

    def test_repeated_strengthening_accrues(self, tmp_path, monkeypatch):
        """Multiple Hebbian updates accumulate. After N applications of
        the default delta, confidence grew by N * delta (until cap)."""
        _setup(tmp_path, monkeypatch)
        a = _make_knowledge("entry a")
        b = _make_knowledge("entry b")
        edge = create_edge(a, b, "RELATED_TO", confidence=0.5)
        for _ in range(5):
            strengthen_edge(edge.edge_id)
        # Final confidence = 0.5 + 5 * 0.02 = 0.6
        final = find_edge(a, b, "RELATED_TO")
        assert final is not None
        assert abs(final.confidence - 0.6) < 1e-9

    def test_custom_delta_works(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        a = _make_knowledge("entry a")
        b = _make_knowledge("entry b")
        edge = create_edge(a, b, "RELATED_TO", confidence=0.3)
        new_conf = strengthen_edge(edge.edge_id, delta=0.1)
        assert abs(new_conf - 0.4) < 1e-9


class TestHebbianGradient:
    """The whole point: re-discovered edges climb the confidence gradient
    while one-time edges stay where they started. This pins the
    qualitative gradient that the streamlining design promises."""

    def test_recurring_edge_outranks_one_time_edge(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        a = _make_knowledge("a")
        b = _make_knowledge("b")
        c = _make_knowledge("c")
        d = _make_knowledge("d")

        recurring_edge = create_edge(a, b, "RELATED_TO", confidence=0.5)
        # one-time edge: created but never re-strengthened
        create_edge(c, d, "RELATED_TO", confidence=0.5)

        # Simulate 10 sleep cycles where the recurring pair shows up
        # again each time (Hebbian strengthens it). The one-time pair
        # never recurs.
        for _ in range(10):
            strengthen_edge(recurring_edge.edge_id)

        recurring = find_edge(a, b, "RELATED_TO")
        one_time = find_edge(c, d, "RELATED_TO")

        assert recurring is not None and one_time is not None
        assert recurring.confidence > one_time.confidence
        # The recurring edge has accumulated evidence; the one-time edge
        # has not.
        assert abs(recurring.confidence - 0.7) < 1e-9  # 0.5 + 10 * 0.02
        assert abs(one_time.confidence - 0.5) < 1e-9  # unchanged
