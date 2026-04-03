"""Tests for the opinion store — structured judgments with evidence tracking."""

import pytest

from divineos.core.opinion_store import (
    challenge_opinion,
    count_opinions,
    format_opinions,
    get_opinion_history,
    get_opinions,
    init_opinion_table,
    store_opinion,
    strengthen_opinion,
)


@pytest.fixture(autouse=True)
def _setup():
    init_opinion_table()


class TestStoreOpinion:
    """Basic opinion storage."""

    def test_store_returns_id(self):
        oid = store_opinion("error handling", "Two-tier pattern works best for CLI tools")
        assert oid.startswith("op-")

    def test_stored_opinion_retrievable(self):
        store_opinion("testing", "Real DB tests beat mocks every time")
        opinions = get_opinions(topic="testing")
        assert len(opinions) >= 1
        assert "Real DB tests" in opinions[0]["position"]

    def test_default_confidence(self):
        store_opinion("defaults", "Sensible defaults save time")
        opinions = get_opinions(topic="defaults")
        assert opinions[0]["confidence"] == 0.7

    def test_custom_confidence(self):
        store_opinion("strong", "Append-only is non-negotiable", confidence=0.95)
        opinions = get_opinions(topic="strong")
        assert opinions[0]["confidence"] == 0.95

    def test_evidence_stored(self):
        store_opinion(
            "small PRs",
            "Small PRs ship faster",
            evidence=["Grok session showed batching works", "DivineOS history confirms"],
        )
        opinions = get_opinions(topic="small PRs")
        assert len(opinions[0]["evidence_for"]) == 2

    def test_tags_stored(self):
        store_opinion("tags", "Tags help", tags=["process", "workflow"])
        opinions = get_opinions(topic="tags")
        assert "process" in opinions[0]["tags"]


class TestOpinionEvolution:
    """Opinions evolve — supersession, not overwrite."""

    def test_same_topic_supersedes(self):
        store_opinion("refactoring", "Big bang rewrites work fine")
        store_opinion("refactoring", "Incremental refactoring is safer")
        opinions = get_opinions(topic="refactoring")
        # Only the active (latest) opinion shows
        assert len(opinions) == 1
        assert "Incremental" in opinions[0]["position"]

    def test_superseded_opinion_has_pointer(self):
        store_opinion("approach", "Waterfall is fine")
        store_opinion("approach", "Iterative is better")
        # Get all including superseded
        all_opinions = get_opinions(topic="approach", active_only=False)
        assert len(all_opinions) == 2
        superseded = [o for o in all_opinions if o["superseded_by"] is not None]
        assert len(superseded) == 1

    def test_opinion_history_shows_evolution(self):
        store_opinion("design", "Monolith first")
        store_opinion("design", "Modular from the start")
        store_opinion("design", "Modular but start simple")
        history = get_opinion_history("design")
        assert len(history) == 3
        assert "Monolith" in history[0]["position"]
        assert "start simple" in history[2]["position"]


class TestStrengthenAndChallenge:
    """Evidence updates confidence."""

    def test_strengthen_increases_confidence(self):
        oid = store_opinion("pattern", "Context managers are clean", confidence=0.6)
        new_conf = strengthen_opinion(oid, "Used successfully in pipeline_gates.py")
        assert new_conf == pytest.approx(0.65)

    def test_strengthen_caps_at_one(self):
        oid = store_opinion("cap", "Will hit ceiling", confidence=0.98)
        new_conf = strengthen_opinion(oid, "More evidence")
        assert new_conf == 1.0

    def test_challenge_decreases_confidence(self):
        oid = store_opinion("shaky", "Might not hold", confidence=0.7)
        new_conf = challenge_opinion(oid, "Found counterexample")
        assert new_conf == pytest.approx(0.6)

    def test_challenge_floors_at_point_one(self):
        oid = store_opinion("weak", "Barely standing", confidence=0.15)
        new_conf = challenge_opinion(oid, "Another counter")
        assert new_conf == 0.1

    def test_challenge_increments_revision_count(self):
        oid = store_opinion("revised", "Will change", confidence=0.7)
        challenge_opinion(oid, "First challenge")
        challenge_opinion(oid, "Second challenge")
        opinions = get_opinions(topic="revised")
        assert opinions[0]["revision_count"] == 2

    def test_nonexistent_opinion_returns_zero(self):
        assert strengthen_opinion("op-doesnotexist", "evidence") == 0.0
        assert challenge_opinion("op-doesnotexist", "evidence") == 0.0


class TestCountAndFormat:
    """Counting and display."""

    def test_count_opinions(self):
        store_opinion("count1", "First opinion")
        store_opinion("count2", "Second opinion", confidence=0.9)
        counts = count_opinions()
        assert counts["active"] >= 2
        assert counts["total"] >= 2

    def test_format_opinions_empty(self):
        # When no opinions match a very specific topic
        result = format_opinions([])
        assert result == "No opinions formed yet."

    def test_format_opinions_shows_markers(self):
        store_opinion("strong_topic", "Strongly held", confidence=0.9)
        store_opinion("medium_topic", "Medium held", confidence=0.6)
        opinions = get_opinions()
        result = format_opinions(opinions)
        assert "◆" in result  # strong
        assert "◇" in result  # medium

    def test_filter_by_min_confidence(self):
        store_opinion("low_conf", "Not sure about this", confidence=0.3)
        store_opinion("high_conf", "Very sure about this", confidence=0.9)
        high = get_opinions(min_confidence=0.8)
        topics = [o["topic"] for o in high]
        assert "high_conf" in topics
        assert "low_conf" not in topics
