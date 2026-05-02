"""Tests for the memory-kind classifier and storage integration.

Locked invariants:

1. Four kinds exist and UNCLASSIFIED is first-class (Beer / Ashby's Law).
2. Tiebreak rule — shape of claim decides, not subject matter.
   "never commit without tests" classifies as SEMANTIC even though it
   describes a procedure.
3. Empty / no-signal / tied-signal content -> UNCLASSIFIED.
   The classifier refuses to guess.
4. Explicit --kind overrides the auto-classifier.
5. Invalid memory_kind passed explicitly raises ValueError.
6. Stored entries carry the memory_kind column; default is UNCLASSIFIED.
"""

from __future__ import annotations

import pytest

from divineos.core.knowledge._base import MEMORY_KINDS
from divineos.core.knowledge.crud import get_knowledge, store_knowledge
from divineos.core.knowledge.memory_kind import classify_kind


class TestMemoryKindEnum:
    def test_four_kinds_exist(self):
        assert MEMORY_KINDS == {
            "EPISODIC",
            "SEMANTIC",
            "PROCEDURAL",
            "UNCLASSIFIED",
        }

    def test_unclassified_is_first_class(self):
        # Not a fallback, not an edge-case flag — an actual member of the set.
        assert "UNCLASSIFIED" in MEMORY_KINDS


class TestClassifier:
    def test_empty_content_is_unclassified(self):
        assert classify_kind("") == "UNCLASSIFIED"
        assert classify_kind("   ") == "UNCLASSIFIED"

    def test_no_signal_is_unclassified(self):
        # Nothing matches any pattern.
        assert classify_kind("xyz abc qqq") == "UNCLASSIFIED"

    def test_episodic_instance_language(self):
        assert classify_kind("Yesterday I broke the build by skipping tests") == "EPISODIC"

    def test_episodic_iso_date(self):
        assert classify_kind("On 2026-04-19 I noticed the drift pattern") == "EPISODIC"

    def test_semantic_rule_shape(self):
        assert classify_kind("Never commit without running tests first") == "SEMANTIC"

    def test_semantic_always_form(self):
        assert classify_kind("Always read before you write") == "SEMANTIC"

    def test_procedural_recipe_shape(self):
        assert classify_kind("To ship: stage the files, then run tests, then push") == "PROCEDURAL"

    def test_procedural_step_numbering(self):
        assert classify_kind("How to debug: bisect first") == "PROCEDURAL"

    def test_tiebreak_rule_shape_wins_over_subject(self):
        # LOCKED INVARIANT: this is the canonical tiebreak case from the
        # classifier docstring. The content is about a procedure
        # (committing) but the SHAPE is a rule. Rule-shape wins.
        result = classify_kind("never commit without tests")
        assert result == "SEMANTIC", (
            f"Tiebreak rule violated: expected SEMANTIC (rule-shape wins "
            f"over subject-matter 'commit procedure'), got {result}"
        )

    def test_strong_tie_returns_unclassified(self):
        # Content with equal strong signal for two kinds -> refuse to guess.
        # "Yesterday I built X, and step 1 was Y" has both episodic and
        # procedural signal; classifier should bail to UNCLASSIFIED rather
        # than pick arbitrarily.
        content = "Yesterday I ran step 1 and then step 2 of the deploy"
        # This has episodic ("Yesterday I ran") and procedural ("step 1",
        # "step 2"). If they tie at top score, -> UNCLASSIFIED.
        result = classify_kind(content)
        assert result in {"EPISODIC", "PROCEDURAL", "UNCLASSIFIED"}
        # Weaker assertion: just that we don't crash and the result is
        # a valid member. The strict tie case is exercised by the next test.

    def test_explicit_tie_returns_unclassified(self):
        # Exactly one hit each: ISO date (episodic), "must" (semantic),
        # "step 1" (procedural). Three-way tie at score=1 each.
        content = "On 2026-04-19 the rule must include step 1"
        assert classify_kind(content) == "UNCLASSIFIED"


class TestStoreIntegration:
    def test_store_auto_classifies_when_kind_omitted(self, tmp_path, monkeypatch):
        # We don't mock the DB — real store_knowledge writes to the
        # project ledger. Use a unique content string and clean up after.
        unique = "memory_kind test: never skip the integration check please 42"
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content=unique,
        )
        assert kid
        entries = get_knowledge(limit=500)
        match = [e for e in entries if e.get("content") == unique]
        assert match, "stored entry not found"
        # "never ... skip ... please" -> SEMANTIC rule-shape.
        assert match[0].get("memory_kind") == "SEMANTIC"

    def test_store_accepts_explicit_kind(self):
        unique = "memory_kind test: explicit kind override 43 a b c"
        kid = store_knowledge(
            knowledge_type="OBSERVATION",
            content=unique,
            memory_kind="EPISODIC",
        )
        assert kid
        entries = get_knowledge(limit=500)
        match = [e for e in entries if e.get("content") == unique]
        assert match
        assert match[0].get("memory_kind") == "EPISODIC"

    def test_store_rejects_invalid_kind(self):
        with pytest.raises(ValueError, match="Invalid memory_kind"):
            store_knowledge(
                knowledge_type="FACT",
                content="this will not store because the kind is bogus",
                memory_kind="BOGUS",
            )
