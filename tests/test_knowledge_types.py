"""Tests for knowledge type reorganization: PREFERENCE, INSTRUCTION, DIRECTION split."""

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge import KNOWLEDGE_TYPES
from divineos.core.knowledge.crud import get_knowledge, store_knowledge
from divineos.core.knowledge.deep_extraction import _classify_user_direction


@pytest.fixture(autouse=True)
def _init():
    init_knowledge_table()


class TestClassifyUserDirection:
    def test_instruction_always(self):
        assert _classify_user_direction("Always run tests after changes") == "INSTRUCTION"

    def test_instruction_never(self):
        assert _classify_user_direction("Never skip the briefing") == "INSTRUCTION"

    def test_instruction_make_sure(self):
        assert _classify_user_direction("Make sure you read before editing") == "INSTRUCTION"

    def test_instruction_check(self):
        assert _classify_user_direction("Check all affected areas after a fix") == "INSTRUCTION"

    def test_preference_prefer(self):
        assert _classify_user_direction("I prefer snake_case for everything") == "PREFERENCE"

    def test_preference_style(self):
        assert (
            _classify_user_direction("Use a conversational style, not spec language")
            == "PREFERENCE"
        )

    def test_preference_convention(self):
        assert _classify_user_direction("Follow PEP 8 convention for naming") == "PREFERENCE"

    def test_direction_general(self):
        assert _classify_user_direction("Focus on fixing known issues first") == "DIRECTION"

    def test_direction_fallback(self):
        assert _classify_user_direction("The OS is not for tasks, it IS the project") == "DIRECTION"


class TestKnowledgeTypesIncludeNew:
    def test_instruction_in_types(self):
        assert "INSTRUCTION" in KNOWLEDGE_TYPES

    def test_preference_in_types(self):
        assert "PREFERENCE" in KNOWLEDGE_TYPES

    def test_can_store_instruction(self):
        store_knowledge(
            knowledge_type="INSTRUCTION",
            content="Always run tests after code changes.",
            confidence=0.9,
        )
        entries = get_knowledge(knowledge_type="INSTRUCTION")
        assert any(e["knowledge_type"] == "INSTRUCTION" for e in entries)

    def test_can_store_preference(self):
        store_knowledge(
            knowledge_type="PREFERENCE",
            content="I prefer conversational tone over spec language.",
            confidence=0.9,
        )
        entries = get_knowledge(knowledge_type="PREFERENCE")
        assert any(e["knowledge_type"] == "PREFERENCE" for e in entries)


class TestReclassifyDirections:
    def test_reclassify_moves_instructions(self):
        from divineos.core.knowledge.migration import reclassify_directions

        store_knowledge(
            knowledge_type="DIRECTION",
            content="Always run tests after code changes. No exceptions.",
            confidence=0.9,
        )
        counts = reclassify_directions()
        assert counts["instruction"] >= 1

    def test_reclassify_moves_preferences(self):
        from divineos.core.knowledge.migration import reclassify_directions

        store_knowledge(
            knowledge_type="DIRECTION",
            content="I prefer snake_case naming convention for all files.",
            confidence=0.9,
        )
        counts = reclassify_directions()
        assert counts["preference"] >= 1

    def test_reclassify_leaves_general_directions(self):
        from divineos.core.knowledge.migration import reclassify_directions

        store_knowledge(
            knowledge_type="DIRECTION",
            content="The OS is not for tasks, it IS the project.",
            confidence=0.9,
        )
        counts = reclassify_directions()
        assert counts["unchanged"] >= 1

    def test_reclassify_idempotent(self):
        from divineos.core.knowledge.migration import reclassify_directions

        store_knowledge(
            knowledge_type="DIRECTION",
            content="Always check the briefing at session start.",
            confidence=0.9,
        )
        reclassify_directions()
        counts2 = reclassify_directions()
        # Second run should find nothing to reclassify (already INSTRUCTION)
        assert counts2["instruction"] == 0
        assert counts2["preference"] == 0


class TestCurationWithNewTypes:
    def test_encouragement_archived_after_7_days(self):
        import time

        from divineos.core.knowledge.curation import assign_layer

        entry = {
            "knowledge_type": "PRINCIPLE",
            "created_at": time.time() - (8 * 86400),  # 8 days old
            "confidence": 0.8,
            "access_count": 2,
            "maturity": "RAW",
            "source": "STATED",
            "corroboration_count": 0,
            "tags": '["encouragement", "auto-extracted"]',
        }
        assert assign_layer(entry) == "archive"

    def test_fresh_encouragement_stays_active(self):
        import time

        from divineos.core.knowledge.curation import assign_layer

        entry = {
            "knowledge_type": "PRINCIPLE",
            "created_at": time.time() - (2 * 86400),  # 2 days old
            "confidence": 0.8,
            "access_count": 2,
            "maturity": "RAW",
            "source": "STATED",
            "corroboration_count": 0,
            "tags": '["encouragement", "auto-extracted"]',
        }
        assert assign_layer(entry) == "active"

    def test_correction_with_corroboration_goes_stable(self):
        import time

        from divineos.core.knowledge.curation import assign_layer

        entry = {
            "knowledge_type": "PRINCIPLE",
            "created_at": time.time() - (5 * 86400),  # 5 days old
            "confidence": 0.8,
            "access_count": 5,
            "maturity": "TESTED",
            "source": "CORRECTED",
            "corroboration_count": 3,
            "tags": "[]",
        }
        assert assign_layer(entry) == "stable"
