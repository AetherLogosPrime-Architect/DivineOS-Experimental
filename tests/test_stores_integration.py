"""Integration tests for all store classes (PatternStore, LearningAuditStore, DecisionStore).

These tests verify that all three stores work together correctly without mocking the ledger.
Tests cover:
- Patterns can be stored and retrieved
- Audits can be stored and retrieved
- Decisions can be stored and retrieved
- All three stores work together in realistic workflows
- Data integrity is maintained across stores
- Ledger persistence works correctly
"""

import uuid
from datetime import datetime

import pytest

from divineos.agent_integration.decision_store import DecisionStore
from divineos.agent_integration.learning_audit_store import LearningAuditStore
from divineos.agent_integration.pattern_store import PatternStore


class TestStoreIntegrationBasics:
    """Test basic integration of all three stores."""

    def test_all_stores_initialize(self) -> None:
        """Test that all three stores can be initialized."""
        pattern_store = PatternStore()
        audit_store = LearningAuditStore()
        decision_store = DecisionStore()

        assert pattern_store is not None
        assert audit_store is not None
        assert decision_store is not None


class TestPatternAndDecisionIntegration:
    """Test integration between PatternStore and DecisionStore."""

    def test_store_pattern_then_use_in_decision(self) -> None:
        """Test storing a pattern and then using it in a decision."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()
        session_id = str(uuid.uuid4())

        # Store a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Type System First",
            description="Always check type system first when seeing cascading errors",
            preconditions={"phase": "bugfix"},
            occurrences=5,
            successes=4,
            confidence=0.8,
        )

        # Use the pattern in a decision
        decision_store.store_decision(
            session_id=session_id,
            task="Fix cascading type errors",
            chosen_pattern=pattern_id,
            pattern_confidence=0.8,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100.0,
                "alternative_costs": [],
                "default_cost": 300.0,
                "counterfactual_type": "estimated",
            },
        )

        # Verify both are stored
        retrieved_pattern = pattern_store.get_pattern(pattern_id)
        assert retrieved_pattern is not None
        assert retrieved_pattern["pattern_id"] == pattern_id

        decisions = decision_store.get_decisions_for_pattern(pattern_id)
        assert len(decisions) > 0
        assert decisions[0]["chosen_pattern"] == pattern_id

    def test_multiple_decisions_reference_same_pattern(self) -> None:
        """Test that multiple decisions can reference the same pattern."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()

        # Store a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="tactical",
            name="Compression at 150k",
            description="Use compression when token budget reaches 150k",
            preconditions={"token_budget_min": 150000},
            occurrences=10,
            successes=9,
            confidence=0.85,
        )

        # Create multiple decisions using this pattern
        for i in range(3):
            session_id = str(uuid.uuid4())
            decision_store.store_decision(
                session_id=session_id,
                task=f"Compress tokens (attempt {i + 1})",
                chosen_pattern=pattern_id,
                pattern_confidence=0.85,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 50.0 + i * 10,
                    "alternative_costs": [],
                    "default_cost": 200.0,
                    "counterfactual_type": "estimated",
                },
            )

        # Verify all decisions reference the pattern
        decisions = decision_store.get_decisions_for_pattern(pattern_id)
        assert len(decisions) >= 3
        for decision in decisions:
            assert decision["chosen_pattern"] == pattern_id

    def test_decision_with_outcome_updates_pattern(self) -> None:
        """Test storing a decision with outcome and then updating pattern confidence."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()
        session_id = str(uuid.uuid4())

        # Store a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Test Pattern",
            description="Test pattern for outcome validation",
            preconditions={},
            occurrences=1,
            successes=1,
            confidence=0.5,
        )

        # Store a decision with outcome
        decision_id = decision_store.store_decision(
            session_id=session_id,
            task="Test task",
            chosen_pattern=pattern_id,
            pattern_confidence=0.5,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100.0,
                "alternative_costs": [],
                "default_cost": 300.0,
                "counterfactual_type": "measured",
            },
            outcome={
                "success": True,
                "primary_outcome": "Task completed successfully",
                "violations_introduced": 0,
                "token_efficiency": 0.95,
                "rework_needed": False,
            },
        )

        # Update pattern confidence based on outcome
        success = pattern_store.update_pattern_confidence(
            pattern_id=pattern_id,
            delta=0.1,
            reason="Successful outcome with no violations",
            source_event_id=decision_id,
        )

        assert success is True

        # Verify pattern was updated
        updated_pattern = pattern_store.get_pattern(pattern_id)
        assert updated_pattern is not None
        assert updated_pattern["confidence"] == 0.6
        assert decision_id in updated_pattern["source_events"]


class TestPatternAndAuditIntegration:
    """Test integration between PatternStore and LearningAuditStore."""

    def test_audit_references_patterns(self) -> None:
        """Test that an audit can reference patterns."""
        pattern_store = PatternStore()
        audit_store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        # Store some patterns
        pattern_ids = []
        for i in range(3):
            pattern_id = pattern_store.store_pattern(
                pattern_type="structural" if i < 2 else "tactical",
                name=f"Pattern {i + 1}",
                description=f"Test pattern {i + 1}",
                preconditions={},
                occurrences=i + 1,
                successes=i,
                confidence=0.5 + i * 0.1,
            )
            pattern_ids.append(pattern_id)

        # Create an audit that references these patterns
        low_confidence_patterns = [
            {
                "pattern_id": pattern_ids[0],
                "name": "Pattern 1",
                "confidence": 0.5,
                "reason": "Low confidence, needs more validation",
            }
        ]

        audit_id = audit_store.store_audit(
            session_id=session_id,
            low_confidence_patterns=low_confidence_patterns,
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )

        # Verify audit was stored
        audit = audit_store.get_latest_audit()
        assert audit is not None
        assert audit["audit_id"] == audit_id
        assert len(audit["low_confidence_patterns"]) == 1
        assert audit["low_confidence_patterns"][0]["pattern_id"] == pattern_ids[0]

    def test_audit_identifies_gaps_in_patterns(self) -> None:
        """Test that audit can identify gaps in pattern coverage."""
        pattern_store = PatternStore()
        audit_store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        # Store a pattern for one phase
        pattern_store.store_pattern(
            pattern_type="structural",
            name="Bugfix Pattern",
            description="Pattern for bugfix phase",
            preconditions={"phase": "bugfix"},
            occurrences=5,
            successes=4,
            confidence=0.8,
        )

        # Create an audit noting gaps for other phases
        pattern_gaps = [
            {
                "gap_type": "phase_coverage",
                "description": "No patterns for feature development phase",
            },
            {
                "gap_type": "phase_coverage",
                "description": "No patterns for refactoring phase",
            },
        ]

        audit_store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=pattern_gaps,
            risky_assumptions=[],
        )

        # Verify audit was stored with gaps
        audit = audit_store.get_latest_audit()
        assert audit is not None
        assert len(audit["pattern_gaps"]) == 2


class TestAllThreeStoresWorkflow:
    """Test realistic workflows using all three stores together."""

    def test_complete_learning_cycle_workflow(self) -> None:
        """Test a complete learning cycle: store patterns, make decisions, audit results."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()
        audit_store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        # Phase 1: Store initial patterns
        pattern_ids = []
        for i in range(3):
            pattern_id = pattern_store.store_pattern(
                pattern_type="structural" if i == 0 else "tactical",
                name=f"Pattern {i + 1}",
                description=f"Pattern for task type {i + 1}",
                preconditions={"phase": "bugfix"} if i == 0 else {},
                occurrences=5 + i,
                successes=4 + i,
                confidence=0.7 + i * 0.05,
            )
            pattern_ids.append(pattern_id)

        # Phase 2: Make decisions using these patterns
        decision_ids = []
        for i, pattern_id in enumerate(pattern_ids):
            decision_id = decision_store.store_decision(
                session_id=session_id,
                task=f"Task using pattern {i + 1}",
                chosen_pattern=pattern_id,
                pattern_confidence=0.7 + i * 0.05,
                alternatives_considered=[
                    {
                        "pattern_id": pattern_ids[(i + 1) % len(pattern_ids)],
                        "name": "Alternative pattern",
                        "confidence": 0.6,
                        "why_rejected": "Lower confidence",
                    }
                ],
                counterfactual={
                    "chosen_cost": 100.0 + i * 10,
                    "alternative_costs": [150.0 + i * 10],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
                outcome={
                    "success": i < 2,  # First two succeed, third fails
                    "primary_outcome": "Success" if i < 2 else "Failed",
                    "violations_introduced": 0 if i < 2 else 1,
                    "token_efficiency": 0.95 if i < 2 else 0.5,
                    "rework_needed": False if i < 2 else True,
                },
            )
            decision_ids.append(decision_id)

        # Phase 3: Update pattern confidence based on outcomes
        for i, pattern_id in enumerate(pattern_ids):
            delta = 0.1 if i < 2 else -0.2  # Reward successes, penalize failures
            pattern_store.update_pattern_confidence(
                pattern_id=pattern_id,
                delta=delta,
                reason="Outcome-based update",
                source_event_id=decision_ids[i],
            )

        # Phase 4: Generate audit
        low_confidence_patterns = [
            {
                "pattern_id": pattern_ids[2],
                "name": "Pattern 3",
                "confidence": 0.65,
                "reason": "Failed in recent session",
            }
        ]

        audit_store.store_audit(
            session_id=session_id,
            low_confidence_patterns=low_confidence_patterns,
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )

        # Verify all components are connected
        audit = audit_store.get_latest_audit()
        assert audit is not None
        assert len(audit["low_confidence_patterns"]) == 1

        for pattern_id in pattern_ids:
            pattern = pattern_store.get_pattern(pattern_id)
            assert pattern is not None
            decisions = decision_store.get_decisions_for_pattern(pattern_id)
            assert len(decisions) > 0

    def test_pattern_query_with_context_matching(self) -> None:
        """Test querying patterns with context matching in a workflow."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()

        # Store patterns with different preconditions
        bugfix_pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Bugfix Pattern",
            description="Pattern for bugfix phase",
            preconditions={"phase": "bugfix"},
            occurrences=10,
            successes=9,
            confidence=0.85,
        )

        feature_pattern_id = pattern_store.store_pattern(
            pattern_type="tactical",
            name="Feature Pattern",
            description="Pattern for feature development",
            preconditions={"phase": "feature"},
            occurrences=8,
            successes=6,
            confidence=0.75,
        )

        # Query patterns for bugfix context
        bugfix_patterns = pattern_store.query_patterns(preconditions={"phase": "bugfix"})
        assert len(bugfix_patterns) > 0
        assert any(p["pattern_id"] == bugfix_pattern_id for p in bugfix_patterns)
        assert not any(p["pattern_id"] == feature_pattern_id for p in bugfix_patterns)

        # Query patterns for feature context
        feature_patterns = pattern_store.query_patterns(preconditions={"phase": "feature"})
        assert len(feature_patterns) > 0
        assert any(p["pattern_id"] == feature_pattern_id for p in feature_patterns)
        assert not any(p["pattern_id"] == bugfix_pattern_id for p in feature_patterns)

        # Make decisions using context-matched patterns
        for pattern_id in [bugfix_pattern_id, feature_pattern_id]:
            decision_store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Context-matched task",
                chosen_pattern=pattern_id,
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
            )

        # Verify decisions are retrievable
        for pattern_id in [bugfix_pattern_id, feature_pattern_id]:
            decisions = decision_store.get_decisions_for_pattern(pattern_id)
            assert len(decisions) > 0


class TestDataIntegrityAcrossStores:
    """Test that data integrity is maintained across stores."""

    def test_pattern_content_hash_integrity(self) -> None:
        """Test that pattern content hashes are computed correctly."""
        pattern_store = PatternStore()

        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Integrity Test Pattern",
            description="Test pattern for integrity verification",
            preconditions={"phase": "bugfix"},
            occurrences=5,
            successes=4,
            confidence=0.8,
        )

        pattern = pattern_store.get_pattern(pattern_id)
        assert pattern is not None
        assert "content_hash" in pattern

        # Verify hash is 32 characters (SHA256 truncated)
        assert len(pattern["content_hash"]) == 32

        # Verify hash is a valid hex string
        try:
            int(pattern["content_hash"], 16)
        except ValueError:
            pytest.fail("content_hash is not a valid hex string")

    def test_decision_content_hash_integrity(self) -> None:
        """Test that decision content hashes are computed correctly."""
        decision_store = DecisionStore()
        session_id = str(uuid.uuid4())
        pattern_id = str(uuid.uuid4())

        decision_store.store_decision(
            session_id=session_id,
            task="Integrity test task",
            chosen_pattern=pattern_id,
            pattern_confidence=0.8,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100.0,
                "alternative_costs": [],
                "default_cost": 300.0,
                "counterfactual_type": "estimated",
            },
        )

        decisions = decision_store.get_decisions_for_pattern(pattern_id)
        assert len(decisions) > 0
        decision = decisions[0]
        assert "content_hash" in decision
        assert len(decision["content_hash"]) == 32

    def test_audit_content_hash_integrity(self) -> None:
        """Test that audit content hashes are computed correctly."""
        audit_store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        audit_store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )

        audit = audit_store.get_latest_audit()
        assert audit is not None
        assert "content_hash" in audit
        assert len(audit["content_hash"]) == 32

    def test_timestamp_ordering_across_stores(self) -> None:
        """Test that timestamps are ordered correctly across stores."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()
        audit_store = LearningAuditStore()
        session_id = str(uuid.uuid4())

        # Store pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Timestamp Test",
            description="Test pattern for timestamp ordering",
            preconditions={},
            occurrences=1,
            successes=1,
            confidence=0.5,
        )

        pattern = pattern_store.get_pattern(pattern_id)
        assert pattern is not None
        pattern_timestamp = datetime.fromisoformat(pattern["created_at"])

        # Store decision
        decision_store.store_decision(
            session_id=session_id,
            task="Timestamp test",
            chosen_pattern=pattern_id,
            pattern_confidence=0.5,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100.0,
                "alternative_costs": [],
                "default_cost": 300.0,
                "counterfactual_type": "estimated",
            },
        )

        decisions = decision_store.get_decisions_for_pattern(pattern_id)
        assert len(decisions) > 0
        decision_timestamp = datetime.fromisoformat(decisions[0]["timestamp"])

        # Store audit
        audit_store.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )

        audit = audit_store.get_latest_audit()
        assert audit is not None
        audit_timestamp = datetime.fromisoformat(audit["timestamp"])

        # Verify timestamps are in order (pattern <= decision <= audit)
        assert pattern_timestamp <= decision_timestamp
        assert decision_timestamp <= audit_timestamp


class TestEdgeCases:
    """Test edge cases in store integration."""

    def test_empty_stores(self) -> None:
        """Test querying empty stores."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()
        audit_store = LearningAuditStore()

        # Query empty pattern store
        patterns = pattern_store.query_patterns(preconditions={})
        assert isinstance(patterns, list)

        # Query empty decision store
        decisions = decision_store.get_decisions_for_pattern(str(uuid.uuid4()))
        assert decisions == []

        # Query empty audit store
        audit = audit_store.get_latest_audit()
        assert audit is None

    def test_multiple_patterns_same_preconditions(self) -> None:
        """Test storing multiple patterns with same preconditions."""
        pattern_store = PatternStore()

        pattern_ids = []
        for i in range(3):
            pattern_id = pattern_store.store_pattern(
                pattern_type="structural",
                name=f"Pattern {i + 1}",
                description=f"Pattern {i + 1} for bugfix phase",
                preconditions={"phase": "bugfix"},
                occurrences=5 + i,
                successes=4 + i,
                confidence=0.7 + i * 0.05,
            )
            pattern_ids.append(pattern_id)

        # Query should return all patterns
        patterns = pattern_store.query_patterns(preconditions={"phase": "bugfix"})
        assert len(patterns) >= 3
        retrieved_ids = [p["pattern_id"] for p in patterns]
        for pattern_id in pattern_ids:
            assert pattern_id in retrieved_ids

    def test_concurrent_operations_on_same_pattern(self) -> None:
        """Test multiple decisions referencing the same pattern."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()

        # Store a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="tactical",
            name="Concurrent Test Pattern",
            description="Pattern for concurrent operations test",
            preconditions={},
            occurrences=1,
            successes=1,
            confidence=0.5,
        )

        # Create multiple decisions concurrently (simulated)
        for i in range(5):
            decision_store.store_decision(
                session_id=str(uuid.uuid4()),
                task=f"Concurrent task {i + 1}",
                chosen_pattern=pattern_id,
                pattern_confidence=0.5,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0 + i,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
            )

        # Verify all decisions are stored
        decisions = decision_store.get_decisions_for_pattern(pattern_id)
        assert len(decisions) >= 5

    def test_error_handling_with_invalid_references(self) -> None:
        """Test error handling when referencing non-existent patterns."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()

        # Try to get a non-existent pattern
        non_existent_id = str(uuid.uuid4())
        pattern = pattern_store.get_pattern(non_existent_id)
        assert pattern is None

        # Try to get decisions for non-existent pattern
        decisions = decision_store.get_decisions_for_pattern(non_existent_id)
        assert decisions == []

        # Try to update non-existent pattern
        success = pattern_store.update_pattern_confidence(
            pattern_id=non_existent_id,
            delta=0.1,
            reason="Test update",
        )
        assert success is False

    def test_ledger_persistence_across_sessions(self) -> None:
        """Test that data persists in ledger across store instances."""
        # First session: store data
        pattern_store_1 = PatternStore()
        decision_store_1 = DecisionStore()
        audit_store_1 = LearningAuditStore()
        session_id = str(uuid.uuid4())

        pattern_id = pattern_store_1.store_pattern(
            pattern_type="structural",
            name="Persistence Test",
            description="Test pattern for persistence",
            preconditions={},
            occurrences=5,
            successes=4,
            confidence=0.8,
        )

        decision_id = decision_store_1.store_decision(
            session_id=session_id,
            task="Persistence test",
            chosen_pattern=pattern_id,
            pattern_confidence=0.8,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100.0,
                "alternative_costs": [],
                "default_cost": 300.0,
                "counterfactual_type": "estimated",
            },
        )

        audit_id = audit_store_1.store_audit(
            session_id=session_id,
            low_confidence_patterns=[],
            untested_patterns=[],
            pattern_gaps=[],
            risky_assumptions=[],
        )

        # Second session: retrieve data with new store instances
        pattern_store_2 = PatternStore()
        decision_store_2 = DecisionStore()
        audit_store_2 = LearningAuditStore()

        # Verify pattern persists
        retrieved_pattern = pattern_store_2.get_pattern(pattern_id)
        assert retrieved_pattern is not None
        assert retrieved_pattern["pattern_id"] == pattern_id
        assert retrieved_pattern["name"] == "Persistence Test"

        # Verify decision persists
        decisions = decision_store_2.get_decisions_for_pattern(pattern_id)
        assert len(decisions) > 0
        assert decisions[0]["decision_id"] == decision_id

        # Verify audit persists
        audit = audit_store_2.get_latest_audit()
        assert audit is not None
        assert audit["audit_id"] == audit_id
