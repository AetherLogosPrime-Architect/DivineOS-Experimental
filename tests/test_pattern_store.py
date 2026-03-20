"""Unit tests for PatternStore class.

Tests cover all four subtasks:
- 1.1.1 store_pattern() - save Pattern to ledger as AGENT_PATTERN event
- 1.1.2 get_pattern(pattern_id) - retrieve pattern from ledger
- 1.1.3 query_patterns(preconditions) - filter patterns by context
- 1.1.4 update_pattern_confidence() - update confidence with logging
"""

import uuid

import pytest

from divineos.agent_integration.pattern_store import PatternStore
from divineos.core.ledger import get_events


class TestPatternStoreBasics:
    """Test basic PatternStore initialization and setup."""

    def test_pattern_store_initialization(self) -> None:
        """Test that PatternStore initializes correctly."""
        store = PatternStore()
        assert store is not None
        assert store.logger is not None


class TestStorePattern:
    """Test store_pattern() - Subtask 1.1.1."""

    def test_store_pattern_structural(self) -> None:
        """Test storing a structural pattern."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Type System First",
            description="Always check type system first when seeing cascading errors",
            preconditions={"phase": "bugfix"},
            occurrences=5,
            successes=4,
            confidence=0.8,
        )

        assert pattern_id is not None
        assert isinstance(pattern_id, str)
        assert len(pattern_id) > 0

    def test_store_pattern_tactical(self) -> None:
        """Test storing a tactical pattern."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="tactical",
            name="Compression at 150k",
            description="Use compression when token budget reaches 150k",
            preconditions={"token_budget_min": 150000},
            occurrences=10,
            successes=9,
            confidence=0.85,
        )

        assert pattern_id is not None

    def test_store_pattern_with_source_events(self) -> None:
        """Test storing a pattern with source events."""
        store = PatternStore()
        source_events = [str(uuid.uuid4()), str(uuid.uuid4())]

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test Pattern",
            description="Test",
            preconditions={},
            source_events=source_events,
        )

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["source_events"] == source_events

    def test_store_pattern_invalid_type(self) -> None:
        """Test that invalid pattern type raises error."""
        store = PatternStore()

        with pytest.raises(ValueError, match="Invalid pattern_type"):
            store.store_pattern(
                pattern_type="invalid",  # type: ignore
                name="Test",
                description="Test",
                preconditions={},
            )

    def test_store_pattern_invalid_confidence(self) -> None:
        """Test that confidence out of range raises error."""
        store = PatternStore()

        with pytest.raises(ValueError, match="Confidence must be between"):
            store.store_pattern(
                pattern_type="structural",
                name="Test",
                description="Test",
                preconditions={},
                confidence=1.5,
            )

        with pytest.raises(ValueError, match="Confidence must be between"):
            store.store_pattern(
                pattern_type="structural",
                name="Test",
                description="Test",
                preconditions={},
                confidence=-1.5,
            )

    def test_store_pattern_invalid_occurrences(self) -> None:
        """Test that invalid occurrences raises error."""
        store = PatternStore()

        with pytest.raises(ValueError, match="Occurrences and successes must be non-negative"):
            store.store_pattern(
                pattern_type="structural",
                name="Test",
                description="Test",
                preconditions={},
                occurrences=-1,
            )

    def test_store_pattern_successes_exceed_occurrences(self) -> None:
        """Test that successes > occurrences raises error."""
        store = PatternStore()

        with pytest.raises(ValueError, match="Successes cannot exceed occurrences"):
            store.store_pattern(
                pattern_type="structural",
                name="Test",
                description="Test",
                preconditions={},
                occurrences=5,
                successes=10,
            )

    def test_store_pattern_calculates_success_rate(self) -> None:
        """Test that success_rate is calculated correctly."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
            occurrences=10,
            successes=6,
        )

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["success_rate"] == 0.6

    def test_store_pattern_zero_occurrences(self) -> None:
        """Test that zero occurrences results in zero success_rate."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
            occurrences=0,
            successes=0,
        )

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["success_rate"] == 0.0

    def test_store_pattern_has_content_hash(self) -> None:
        """Test that stored pattern has SHA256 content hash (truncated to 32 chars)."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
        )

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert "content_hash" in pattern
        assert len(pattern["content_hash"]) == 32  # SHA256 truncated to 32 chars

    def test_store_pattern_tactical_has_decay_rate(self) -> None:
        """Test that tactical patterns have decay_rate set."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="tactical",
            name="Test",
            description="Test",
            preconditions={},
        )

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["decay_rate"] == 0.05

    def test_store_pattern_structural_no_decay(self) -> None:
        """Test that structural patterns have no decay."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
        )

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["decay_rate"] == 0.0

    def test_store_pattern_has_timestamps(self) -> None:
        """Test that stored pattern has created_at and updated_at."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
        )

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert "created_at" in pattern
        assert "updated_at" in pattern
        assert pattern["created_at"] == pattern["updated_at"]


class TestGetPattern:
    """Test get_pattern() - Subtask 1.1.2."""

    def test_get_pattern_returns_stored_pattern(self) -> None:
        """Test that get_pattern returns the stored pattern."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test Pattern",
            description="Test Description",
            preconditions={"phase": "bugfix"},
            occurrences=5,
            successes=3,
            confidence=0.6,
        )

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["pattern_id"] == pattern_id
        assert pattern["name"] == "Test Pattern"
        assert pattern["description"] == "Test Description"
        assert pattern["pattern_type"] == "structural"
        assert pattern["occurrences"] == 5
        assert pattern["successes"] == 3
        assert pattern["confidence"] == 0.6

    def test_get_pattern_not_found(self) -> None:
        """Test that get_pattern returns None for non-existent pattern."""
        store = PatternStore()
        fake_id = str(uuid.uuid4())

        pattern = store.get_pattern(fake_id)
        assert pattern is None

    def test_get_pattern_preserves_preconditions(self) -> None:
        """Test that preconditions are preserved."""
        store = PatternStore()
        preconditions = {
            "token_budget_min": 100000,
            "token_budget_max": 200000,
            "phase": "feature",
            "codebase_structure": "hash123",
            "constraints": ["no_hook_conflicts"],
        }

        pattern_id = store.store_pattern(
            pattern_type="tactical",
            name="Test",
            description="Test",
            preconditions=preconditions,
        )

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["preconditions"] == preconditions


class TestQueryPatterns:
    """Test query_patterns() - Subtask 1.1.3."""

    def test_query_patterns_empty_result(self) -> None:
        """Test query with no matching patterns."""
        store = PatternStore()

        results = store.query_patterns({"phase": "nonexistent"})
        assert isinstance(results, list)
        assert len(results) == 0

    def test_query_patterns_matches_phase(self) -> None:
        """Test that query matches patterns by phase."""
        store = PatternStore()

        # Store patterns with different phases
        store.store_pattern(
            pattern_type="structural",
            name="Bugfix Pattern",
            description="Test",
            preconditions={"phase": "bugfix"},
            confidence=0.8,
        )

        store.store_pattern(
            pattern_type="structural",
            name="Feature Pattern",
            description="Test",
            preconditions={"phase": "feature"},
            confidence=0.7,
        )

        # Query for bugfix patterns
        results = store.query_patterns({"phase": "bugfix"})
        assert len(results) == 1

    def test_query_patterns_matches_token_budget_range(self) -> None:
        """Test that query matches token budget ranges."""
        store = PatternStore()

        # Store pattern with token budget range
        pattern_id = store.store_pattern(
            pattern_type="tactical",
            name="Test",
            description="Test",
            preconditions={"token_budget_min": 100000, "token_budget_max": 200000},
            confidence=0.8,
        )

        # Query within range
        results = store.query_patterns({"token_budget": 150000})
        assert len(results) == 1
        assert results[0]["pattern_id"] == pattern_id

        # Query below range
        results = store.query_patterns({"token_budget": 50000})
        assert len(results) == 0

        # Query above range
        results = store.query_patterns({"token_budget": 250000})
        assert len(results) == 0

    def test_query_patterns_matches_codebase_structure(self) -> None:
        """Test that query matches codebase structure hash."""
        store = PatternStore()

        store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={"codebase_structure": "hash_abc123"},
            confidence=0.8,
        )

        # Matching structure
        results = store.query_patterns({"codebase_structure": "hash_abc123"})
        assert len(results) == 1

        # Non-matching structure
        results = store.query_patterns({"codebase_structure": "hash_xyz789"})
        assert len(results) == 0

    def test_query_patterns_matches_constraints(self) -> None:
        """Test that query matches all constraints."""
        store = PatternStore()

        store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={"constraints": ["no_hook_conflicts", "no_violations"]},
            confidence=0.8,
        )

        # All constraints satisfied
        results = store.query_patterns(
            {"constraints": ["no_hook_conflicts", "no_violations", "other"]}
        )
        assert len(results) == 1

        # Missing one constraint
        results = store.query_patterns({"constraints": ["no_hook_conflicts"]})
        assert len(results) == 0

    def test_query_patterns_respects_confidence_threshold(self) -> None:
        """Test that query respects min_confidence threshold."""
        store = PatternStore()

        # Store patterns with different confidence levels
        id1 = store.store_pattern(
            pattern_type="structural",
            name="High Confidence",
            description="Test",
            preconditions={},
            confidence=0.9,
        )

        store.store_pattern(
            pattern_type="structural",
            name="Low Confidence",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Query with default threshold (0.65)
        results = store.query_patterns({})
        assert len(results) == 1
        assert results[0]["pattern_id"] == id1

        # Query with lower threshold
        results = store.query_patterns({}, min_confidence=0.4)
        assert len(results) == 2

    def test_query_patterns_excludes_anti_patterns(self) -> None:
        """Test that anti-patterns are excluded by default."""
        store = PatternStore()

        # Store anti-pattern (confidence < -0.5)
        store.store_pattern(
            pattern_type="structural",
            name="Anti-Pattern",
            description="Test",
            preconditions={},
            confidence=-0.6,
        )

        # Store normal pattern
        id2 = store.store_pattern(
            pattern_type="structural",
            name="Normal Pattern",
            description="Test",
            preconditions={},
            confidence=0.8,
        )

        # Query excludes anti-patterns by default
        results = store.query_patterns({})
        assert len(results) == 1
        assert results[0]["pattern_id"] == id2

        # Query can include anti-patterns
        results = store.query_patterns({}, exclude_anti_patterns=False)
        assert len(results) == 2

    def test_query_patterns_sorts_by_confidence(self) -> None:
        """Test that results are sorted by confidence (highest first)."""
        store = PatternStore()

        id1 = store.store_pattern(
            pattern_type="structural",
            name="Low",
            description="Test",
            preconditions={},
            confidence=0.7,
        )

        id2 = store.store_pattern(
            pattern_type="structural",
            name="High",
            description="Test",
            preconditions={},
            confidence=0.9,
        )

        id3 = store.store_pattern(
            pattern_type="structural",
            name="Medium",
            description="Test",
            preconditions={},
            confidence=0.8,
        )

        results = store.query_patterns({}, min_confidence=0.6)
        assert len(results) == 3
        assert results[0]["pattern_id"] == id2  # 0.9
        assert results[1]["pattern_id"] == id3  # 0.8
        assert results[2]["pattern_id"] == id1  # 0.7

    def test_query_patterns_multiple_preconditions(self) -> None:
        """Test query with multiple preconditions."""
        store = PatternStore()

        store.store_pattern(
            pattern_type="tactical",
            name="Test",
            description="Test",
            preconditions={
                "phase": "bugfix",
                "token_budget_min": 100000,
                "token_budget_max": 200000,
            },
            confidence=0.8,
        )

        # All preconditions match
        results = store.query_patterns({"phase": "bugfix", "token_budget": 150000})
        assert len(results) == 1

        # One precondition doesn't match
        results = store.query_patterns({"phase": "feature", "token_budget": 150000})
        assert len(results) == 0


class TestUpdatePatternConfidence:
    """Test update_pattern_confidence() - Subtask 1.1.4."""

    def test_update_pattern_confidence_positive_delta(self) -> None:
        """Test updating confidence with positive delta."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        success = store.update_pattern_confidence(pattern_id, delta=0.2, reason="Pattern succeeded")

        assert success is True
        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["confidence"] == 0.7

    def test_update_pattern_confidence_negative_delta(self) -> None:
        """Test updating confidence with negative delta."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
            confidence=0.8,
        )

        success = store.update_pattern_confidence(pattern_id, delta=-0.3, reason="Pattern failed")

        assert success is True
        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["confidence"] == 0.5

    def test_update_pattern_confidence_clamps_to_max(self) -> None:
        """Test that confidence is clamped to 1.0."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
            confidence=0.9,
        )

        store.update_pattern_confidence(pattern_id, delta=0.5, reason="Test")

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["confidence"] == 1.0

    def test_update_pattern_confidence_clamps_to_min(self) -> None:
        """Test that confidence is clamped to -1.0."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
            confidence=-0.8,
        )

        store.update_pattern_confidence(pattern_id, delta=-0.5, reason="Test")

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["confidence"] == -1.0

    def test_update_pattern_confidence_not_found(self) -> None:
        """Test updating non-existent pattern returns False."""
        store = PatternStore()
        fake_id = str(uuid.uuid4())

        success = store.update_pattern_confidence(fake_id, delta=0.1, reason="Test")

        assert success is False

    def test_update_pattern_confidence_updates_timestamp(self) -> None:
        """Test that updated_at is updated."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
        )

        pattern1 = store.get_pattern(pattern_id)
        assert pattern1 is not None
        original_updated_at = pattern1["updated_at"]

        # Wait a tiny bit and update
        import time

        time.sleep(0.01)

        store.update_pattern_confidence(pattern_id, delta=0.1, reason="Test")

        pattern2 = store.get_pattern(pattern_id)
        assert pattern2 is not None
        assert pattern2["updated_at"] > original_updated_at

    def test_update_pattern_confidence_with_source_event(self) -> None:
        """Test that source_event_id is added to pattern."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
        )

        source_event_id = str(uuid.uuid4())
        store.update_pattern_confidence(
            pattern_id,
            delta=0.1,
            reason="Test",
            source_event_id=source_event_id,
        )

        pattern = store.get_pattern(pattern_id)
        assert pattern is not None
        assert source_event_id in pattern["source_events"]

    def test_update_pattern_confidence_logs_update_event(self) -> None:
        """Test that update is logged as AGENT_PATTERN_UPDATE event."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        store.update_pattern_confidence(pattern_id, delta=0.2, reason="Pattern succeeded")

        # Check that AGENT_PATTERN_UPDATE event was logged
        events = get_events(event_type="AGENT_PATTERN_UPDATE", limit=100)
        update_events = [e for e in events if e.get("payload", {}).get("pattern_id") == pattern_id]
        assert len(update_events) > 0

        update_event = update_events[-1]
        payload = update_event["payload"]
        assert payload["old_confidence"] == 0.5
        assert payload["new_confidence"] == 0.7
        assert payload["delta"] == 0.2
        assert payload["reason"] == "Pattern succeeded"

    def test_update_pattern_confidence_recomputes_hash(self) -> None:
        """Test that content_hash is recomputed after update."""
        store = PatternStore()

        pattern_id = store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        pattern1 = store.get_pattern(pattern_id)
        assert pattern1 is not None
        hash1 = pattern1["content_hash"]

        store.update_pattern_confidence(pattern_id, delta=0.2, reason="Test")

        pattern2 = store.get_pattern(pattern_id)
        assert pattern2 is not None
        hash2 = pattern2["content_hash"]

        # Hash should be different because confidence changed
        assert hash1 != hash2


class TestPreconditionMatching:
    """Test precondition matching logic."""

    def test_preconditions_match_no_preconditions(self) -> None:
        """Test that pattern with no preconditions matches any context."""
        store = PatternStore()

        store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={},
            confidence=0.8,
        )

        # Should match any context
        results = store.query_patterns({"phase": "bugfix", "token_budget": 100000})
        assert len(results) == 1

    def test_preconditions_match_optional_fields(self) -> None:
        """Test that optional precondition fields work correctly."""
        store = PatternStore()

        # Pattern with only phase precondition
        store.store_pattern(
            pattern_type="structural",
            name="Test",
            description="Test",
            preconditions={"phase": "bugfix"},
            confidence=0.8,
        )

        # Should match when phase matches, regardless of other context
        results = store.query_patterns(
            {"phase": "bugfix", "token_budget": 100000, "other": "value"}
        )
        assert len(results) == 1

    def test_preconditions_match_token_budget_boundaries(self) -> None:
        """Test token budget boundary conditions."""
        store = PatternStore()

        store.store_pattern(
            pattern_type="tactical",
            name="Test",
            description="Test",
            preconditions={"token_budget_min": 100000, "token_budget_max": 200000},
            confidence=0.8,
        )

        # Exact boundaries should match
        results = store.query_patterns({"token_budget": 100000})
        assert len(results) == 1

        results = store.query_patterns({"token_budget": 200000})
        assert len(results) == 1

        # Just outside boundaries should not match
        results = store.query_patterns({"token_budget": 99999})
        assert len(results) == 0

        results = store.query_patterns({"token_budget": 200001})
        assert len(results) == 0
