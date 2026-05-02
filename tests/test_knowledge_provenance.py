"""Tests for knowledge provenance — source_entity and related_to fields."""

import pytest

from divineos.core.knowledge import _get_connection, init_knowledge_table
from divineos.core.knowledge.crud import store_knowledge


@pytest.fixture(autouse=True)
def _ensure_schema():
    """Ensure knowledge table has provenance columns."""
    init_knowledge_table()
    yield


class TestSourceEntity:
    def test_default_is_none(self):
        kid = store_knowledge("FACT", "Default source entity test entry xyzzy")
        conn = _get_connection()
        row = conn.execute(
            "SELECT source_entity FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        assert row[0] is None

    def test_stores_entity_name(self):
        kid = store_knowledge(
            "FACT",
            "Auditor found signal extraction is self-referential unique123",
            source_entity="claude_auditor",
        )
        conn = _get_connection()
        row = conn.execute(
            "SELECT source_entity FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        assert row[0] == "claude_auditor"

    def test_different_entities_distinguishable(self):
        kid1 = store_knowledge(
            "FACT",
            "Finding from council lens analysis about Goodhart provenance_test_1",
            source_entity="aether_council",
        )
        kid2 = store_knowledge(
            "FACT",
            "Finding from external audit about closed loops provenance_test_2",
            source_entity="claude_auditor",
        )
        conn = _get_connection()
        r1 = conn.execute(
            "SELECT source_entity FROM knowledge WHERE knowledge_id = ?", (kid1,)
        ).fetchone()
        r2 = conn.execute(
            "SELECT source_entity FROM knowledge WHERE knowledge_id = ?", (kid2,)
        ).fetchone()
        conn.close()
        assert r1[0] == "aether_council"
        assert r2[0] == "claude_auditor"

    def test_query_by_entity(self):
        store_knowledge(
            "FACT",
            "Entity query test from auditor unique_entity_query_test",
            source_entity="claude_auditor",
        )
        store_knowledge(
            "FACT",
            "Entity query test from council unique_entity_query_test2",
            source_entity="aether_council",
        )
        conn = _get_connection()
        rows = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE source_entity = ?",
            ("claude_auditor",),
        ).fetchone()
        conn.close()
        assert rows[0] >= 1


class TestRelatedTo:
    def test_default_is_none(self):
        kid = store_knowledge("FACT", "Default related to test entry abcde")
        conn = _get_connection()
        row = conn.execute(
            "SELECT related_to FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        assert row[0] is None

    def test_stores_related_ids(self):
        kid1 = store_knowledge("FACT", "First finding for linking test qwerty_link1")
        kid2 = store_knowledge(
            "FACT",
            "Second finding that relates to first qwerty_link2",
            related_to=kid1,
        )
        conn = _get_connection()
        row = conn.execute(
            "SELECT related_to FROM knowledge WHERE knowledge_id = ?", (kid2,)
        ).fetchone()
        conn.close()
        assert row[0] == kid1

    def test_multiple_related_ids(self):
        kid1 = store_knowledge("FACT", "Related A for multi-link test multi_a")
        kid2 = store_knowledge("FACT", "Related B for multi-link test multi_b")
        kid3 = store_knowledge(
            "FACT",
            "Synthesis linking to both A and B multi_synth",
            related_to=f"{kid1},{kid2}",
        )
        conn = _get_connection()
        row = conn.execute(
            "SELECT related_to FROM knowledge WHERE knowledge_id = ?", (kid3,)
        ).fetchone()
        conn.close()
        assert kid1 in row[0]
        assert kid2 in row[0]

    def test_combined_entity_and_related(self):
        kid1 = store_knowledge(
            "FACT",
            "Auditor finding for combined test combined_a",
            source_entity="claude_auditor",
        )
        kid2 = store_knowledge(
            "FACT",
            "Council finding related to auditor finding combined_b",
            source_entity="aether_council",
            related_to=kid1,
        )
        conn = _get_connection()
        row = conn.execute(
            "SELECT source_entity, related_to FROM knowledge WHERE knowledge_id = ?",
            (kid2,),
        ).fetchone()
        conn.close()
        assert row[0] == "aether_council"
        assert row[1] == kid1
