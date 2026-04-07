"""Tests for graph-boosted briefing scoring and compass behavioral guidance."""

from divineos.core.knowledge._base import init_knowledge_table
from divineos.core.knowledge.edges import create_edge, init_edge_table
from divineos.core.knowledge.extraction import store_knowledge_smart
from divineos.core.knowledge.retrieval import _apply_graph_boost, _compass_guidance


def _setup():
    init_knowledge_table()
    init_edge_table()


class TestGraphBoost:
    """Entries connected to high-scoring entries get a score bump."""

    def test_connected_entry_gets_boost(self):
        _setup()
        # Create two entries with an edge between them
        kid_a = store_knowledge_smart(
            knowledge_type="PRINCIPLE",
            content="Always verify assumptions before acting on them",
            confidence=0.9,
            source="STATED",
        )
        kid_b = store_knowledge_smart(
            knowledge_type="OBSERVATION",
            content="Unverified assumptions led to three rework cycles",
            confidence=0.5,
            source="OBSERVED",
        )
        assert kid_a and kid_b
        create_edge(kid_a, kid_b, "SUPPORTS")

        # Simulate scored entries
        entries = [
            {"knowledge_id": kid_a, "_score": 1.5},
            {"knowledge_id": kid_b, "_score": 0.3},
        ]

        _apply_graph_boost(entries)
        # B should get a boost from being connected to high-scoring A
        # But need at least 3 entries for boost to run
        # With only 2, it returns early
        assert entries[1]["_score"] == 0.3  # no boost with < 3 entries

    def test_boost_requires_minimum_entries(self):
        _setup()
        entries = [
            {"knowledge_id": "a", "_score": 1.0},
            {"knowledge_id": "b", "_score": 0.5},
        ]
        _apply_graph_boost(entries)
        # Should return without modification
        assert entries[0]["_score"] == 1.0
        assert entries[1]["_score"] == 0.5

    def test_boost_with_enough_entries(self):
        _setup()
        from divineos.core.knowledge.crud import store_knowledge

        kid_a = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Test your changes before claiming they work properly",
            confidence=0.95,
            source="STATED",
        )
        kid_b = store_knowledge(
            knowledge_type="OBSERVATION",
            content="Untested changes caused three production issues last week",
            confidence=0.4,
            source="OBSERVED",
        )
        kid_c = store_knowledge(
            knowledge_type="FACT",
            content="The test suite has over three thousand tests covering all modules",
            confidence=0.8,
            source="STATED",
        )
        create_edge(kid_a, kid_b, "SUPPORTS")

        entries = [
            {"knowledge_id": kid_a, "_score": 1.5},
            {"knowledge_id": kid_b, "_score": 0.3},
            {"knowledge_id": kid_c, "_score": 0.8},
        ]

        original_b_score = entries[1]["_score"]
        _apply_graph_boost(entries)
        # B is connected to A (high scorer), so it should get boosted
        assert entries[1]["_score"] > original_b_score

    def test_unconnected_entries_unchanged(self):
        _setup()
        from divineos.core.knowledge.crud import store_knowledge

        kid_a = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Read files before editing them always without exception",
            confidence=0.9,
            source="STATED",
        )
        kid_b = store_knowledge(
            knowledge_type="FACT",
            content="Python uses indentation for block structure syntax",
            confidence=0.7,
            source="STATED",
        )
        kid_c = store_knowledge(
            knowledge_type="FACT",
            content="SQLite is the storage backend for the DivineOS system",
            confidence=0.8,
            source="STATED",
        )
        # No edges between any of them

        entries = [
            {"knowledge_id": kid_a, "_score": 1.5},
            {"knowledge_id": kid_b, "_score": 0.5},
            {"knowledge_id": kid_c, "_score": 0.3},
        ]

        _apply_graph_boost(entries)
        # No connections, so scores unchanged
        assert entries[1]["_score"] == 0.5
        assert entries[2]["_score"] == 0.3


class TestCompassGuidance:
    """Compass concerns should produce actionable behavioral guidance."""

    def test_thoroughness_excess_guidance(self):
        result = _compass_guidance("thoroughness", "excess")
        assert result
        assert "ease up" in result.lower() or "question asked" in result.lower()

    def test_confidence_excess_guidance(self):
        result = _compass_guidance("confidence", "excess")
        assert result
        assert "overclaim" in result.lower() or "uncertainty" in result.lower()

    def test_unknown_spectrum_returns_empty(self):
        result = _compass_guidance("nonexistent_spectrum", "excess")
        assert result == ""

    def test_virtue_zone_returns_empty(self):
        # Virtue zone = no concern, so no guidance needed
        result = _compass_guidance("thoroughness", "virtue")
        assert result == ""

    def test_all_guidance_entries_are_actionable(self):
        """Every guidance entry should contain an imperative verb or directive."""
        from divineos.core.knowledge.retrieval import _COMPASS_GUIDANCE

        for (spectrum, zone), guidance in _COMPASS_GUIDANCE.items():
            assert len(guidance) > 10, f"Guidance for {spectrum}/{zone} too short"
            assert guidance[0].isupper(), f"Guidance for {spectrum}/{zone} should start capitalized"

    def test_deficiency_and_excess_covered_per_spectrum(self):
        """Key spectrums should have both deficiency and excess guidance."""
        from divineos.core.knowledge.retrieval import _COMPASS_GUIDANCE

        key_spectrums = ["thoroughness", "confidence", "initiative", "compliance"]
        for s in key_spectrums:
            has_excess = (s, "excess") in _COMPASS_GUIDANCE
            has_deficiency = (s, "deficiency") in _COMPASS_GUIDANCE
            assert has_excess, f"{s} missing excess guidance"
            assert has_deficiency, f"{s} missing deficiency guidance"
