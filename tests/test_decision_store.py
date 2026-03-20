"""Unit tests for DecisionStore class.

Tests cover all two subtasks:
- 1.3.1 store_decision() - save decision to ledger as AGENT_DECISION event
- 1.3.2 get_decisions_for_pattern() - retrieve all decisions using a pattern
"""

import uuid

import pytest

from divineos.agent_integration.decision_store import DecisionStore
from divineos.core.ledger import get_events


class TestDecisionStoreBasics:
    """Test basic DecisionStore initialization and setup."""

    def test_decision_store_initialization(self) -> None:
        """Test that DecisionStore initializes correctly."""
        store = DecisionStore()
        assert store is not None
        assert store.logger is not None


class TestStoreDecision:
    """Test store_decision() - Subtask 1.3.1."""

    def test_store_decision_basic(self) -> None:
        """Test storing a basic decision."""
        store = DecisionStore()
        session_id = str(uuid.uuid4())
        pattern_id = str(uuid.uuid4())

        decision_id = store.store_decision(
            session_id=session_id,
            task="Fix authentication bug",
            chosen_pattern=pattern_id,
            pattern_confidence=0.85,
            alternatives_considered=[
                {
                    "pattern_id": str(uuid.uuid4()),
                    "name": "Alternative 1",
                    "confidence": 0.6,
                    "why_rejected": "Lower confidence",
                }
            ],
            counterfactual={
                "chosen_cost": 100.0,
                "alternative_costs": [150.0, 200.0],
                "default_cost": 300.0,
                "counterfactual_type": "estimated",
            },
        )

        assert decision_id is not None
        assert isinstance(decision_id, str)
        assert len(decision_id) > 0

    def test_store_decision_with_outcome(self) -> None:
        """Test storing a decision with outcome information."""
        store = DecisionStore()
        session_id = str(uuid.uuid4())
        pattern_id = str(uuid.uuid4())

        decision_id = store.store_decision(
            session_id=session_id,
            task="Fix authentication bug",
            chosen_pattern=pattern_id,
            pattern_confidence=0.85,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100.0,
                "alternative_costs": [],
                "default_cost": 300.0,
                "counterfactual_type": "measured",
            },
            outcome={
                "success": True,
                "primary_outcome": "Bug fixed, all tests pass",
                "violations_introduced": 0,
                "token_efficiency": 0.95,
                "rework_needed": False,
            },
        )

        assert decision_id is not None

    def test_store_decision_missing_session_id(self) -> None:
        """Test that missing session_id raises error."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="session_id is required"):
            store.store_decision(
                session_id="",
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
            )

    def test_store_decision_missing_task(self) -> None:
        """Test that missing task raises error."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="task is required"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
            )

    def test_store_decision_missing_chosen_pattern(self) -> None:
        """Test that missing chosen_pattern raises error."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="chosen_pattern is required"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern="",
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
            )

    def test_store_decision_invalid_confidence(self) -> None:
        """Test that invalid confidence raises error."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="pattern_confidence must be between"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=1.5,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
            )

        with pytest.raises(ValueError, match="pattern_confidence must be between"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=-1.5,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
            )

    def test_store_decision_invalid_alternatives_type(self) -> None:
        """Test that non-list alternatives raises error."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="alternatives_considered must be a list"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered="not a list",  # type: ignore
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
            )

    def test_store_decision_invalid_counterfactual_type(self) -> None:
        """Test that non-dict counterfactual raises error."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="counterfactual must be a dict"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual="not a dict",  # type: ignore
            )

    def test_store_decision_missing_counterfactual_fields(self) -> None:
        """Test that missing counterfactual fields raise error."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="counterfactual must include chosen_cost"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
            )

        with pytest.raises(ValueError, match="counterfactual must include alternative_costs"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
            )

        with pytest.raises(ValueError, match="counterfactual must include default_cost"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "counterfactual_type": "estimated",
                },
            )

        with pytest.raises(ValueError, match="counterfactual must include counterfactual_type"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                },
            )

    def test_store_decision_invalid_counterfactual_type_value(self) -> None:
        """Test that invalid counterfactual_type value raises error."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="counterfactual_type must be"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "invalid",
                },
            )

    def test_store_decision_invalid_outcome_type(self) -> None:
        """Test that non-dict outcome raises error."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="outcome must be a dict"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
                outcome="not a dict",  # type: ignore
            )

    def test_store_decision_missing_outcome_fields(self) -> None:
        """Test that missing outcome fields raise error."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="outcome must include success"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
                outcome={
                    "primary_outcome": "Test",
                    "violations_introduced": 0,
                    "token_efficiency": 0.9,
                    "rework_needed": False,
                },
            )

    def test_store_decision_outcome_success_not_bool(self) -> None:
        """Test that outcome.success must be bool."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="outcome.success must be a bool"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
                outcome={
                    "success": "yes",  # type: ignore
                    "primary_outcome": "Test",
                    "violations_introduced": 0,
                    "token_efficiency": 0.9,
                    "rework_needed": False,
                },
            )

    def test_store_decision_outcome_rework_not_bool(self) -> None:
        """Test that outcome.rework_needed must be bool."""
        store = DecisionStore()

        with pytest.raises(ValueError, match="outcome.rework_needed must be a bool"):
            store.store_decision(
                session_id=str(uuid.uuid4()),
                task="Test",
                chosen_pattern=str(uuid.uuid4()),
                pattern_confidence=0.8,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0,
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
                outcome={
                    "success": True,
                    "primary_outcome": "Test",
                    "violations_introduced": 0,
                    "token_efficiency": 0.9,
                    "rework_needed": "no",  # type: ignore
                },
            )

    def test_store_decision_has_content_hash(self) -> None:
        """Test that stored decision has SHA256 content hash (truncated to 32 chars)."""
        store = DecisionStore()
        session_id = str(uuid.uuid4())
        pattern_id = str(uuid.uuid4())

        decision_id = store.store_decision(
            session_id=session_id,
            task="Test",
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

        # Retrieve the decision from ledger
        events = get_events(event_type="AGENT_DECISION", limit=10000)
        decision_events = [
            e for e in events if e.get("payload", {}).get("decision_id") == decision_id
        ]
        assert len(decision_events) > 0

        decision = decision_events[-1].get("payload")
        assert decision is not None
        assert "content_hash" in decision
        assert len(decision["content_hash"]) == 32  # SHA256 truncated to 32 chars

    def test_store_decision_has_timestamps(self) -> None:
        """Test that stored decision has timestamp."""
        store = DecisionStore()
        session_id = str(uuid.uuid4())
        pattern_id = str(uuid.uuid4())

        decision_id = store.store_decision(
            session_id=session_id,
            task="Test",
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

        events = get_events(event_type="AGENT_DECISION", limit=10000)
        decision_events = [
            e for e in events if e.get("payload", {}).get("decision_id") == decision_id
        ]
        assert len(decision_events) > 0

        decision = decision_events[-1].get("payload")
        assert decision is not None
        assert "timestamp" in decision
        assert isinstance(decision["timestamp"], str)


class TestGetDecisionsForPattern:
    """Test get_decisions_for_pattern() - Subtask 1.3.2."""

    def test_get_decisions_for_pattern_empty_result(self) -> None:
        """Test query with no matching decisions."""
        store = DecisionStore()
        fake_pattern_id = str(uuid.uuid4())

        results = store.get_decisions_for_pattern(fake_pattern_id)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_get_decisions_for_pattern_single_decision(self) -> None:
        """Test retrieving a single decision for a pattern."""
        store = DecisionStore()
        session_id = str(uuid.uuid4())
        pattern_id = str(uuid.uuid4())

        decision_id = store.store_decision(
            session_id=session_id,
            task="Fix bug",
            chosen_pattern=pattern_id,
            pattern_confidence=0.85,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100.0,
                "alternative_costs": [],
                "default_cost": 300.0,
                "counterfactual_type": "estimated",
            },
        )

        results = store.get_decisions_for_pattern(pattern_id)
        assert len(results) == 1
        assert results[0]["decision_id"] == decision_id
        assert results[0]["chosen_pattern"] == pattern_id

    def test_get_decisions_for_pattern_multiple_decisions(self) -> None:
        """Test retrieving multiple decisions for the same pattern."""
        store = DecisionStore()
        pattern_id = str(uuid.uuid4())

        # Store multiple decisions using the same pattern
        decision_ids = []
        for i in range(3):
            decision_id = store.store_decision(
                session_id=str(uuid.uuid4()),
                task=f"Task {i}",
                chosen_pattern=pattern_id,
                pattern_confidence=0.8 + (i * 0.05),
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100.0 + (i * 10),
                    "alternative_costs": [],
                    "default_cost": 300.0,
                    "counterfactual_type": "estimated",
                },
            )
            decision_ids.append(decision_id)

        results = store.get_decisions_for_pattern(pattern_id)
        assert len(results) == 3

        # All results should have the correct pattern
        for result in results:
            assert result["chosen_pattern"] == pattern_id

        # All decision IDs should be present
        result_ids = [r["decision_id"] for r in results]
        for decision_id in decision_ids:
            assert decision_id in result_ids

    def test_get_decisions_for_pattern_filters_by_pattern(self) -> None:
        """Test that results are filtered by pattern ID."""
        store = DecisionStore()
        pattern_id_1 = str(uuid.uuid4())
        pattern_id_2 = str(uuid.uuid4())

        # Store decisions for different patterns
        decision_id_1 = store.store_decision(
            session_id=str(uuid.uuid4()),
            task="Task 1",
            chosen_pattern=pattern_id_1,
            pattern_confidence=0.8,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100.0,
                "alternative_costs": [],
                "default_cost": 300.0,
                "counterfactual_type": "estimated",
            },
        )

        decision_id_2 = store.store_decision(
            session_id=str(uuid.uuid4()),
            task="Task 2",
            chosen_pattern=pattern_id_2,
            pattern_confidence=0.85,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 110.0,
                "alternative_costs": [],
                "default_cost": 310.0,
                "counterfactual_type": "estimated",
            },
        )

        # Query for pattern 1
        results_1 = store.get_decisions_for_pattern(pattern_id_1)
        assert len(results_1) == 1
        assert results_1[0]["decision_id"] == decision_id_1

        # Query for pattern 2
        results_2 = store.get_decisions_for_pattern(pattern_id_2)
        assert len(results_2) == 1
        assert results_2[0]["decision_id"] == decision_id_2

    def test_get_decisions_for_pattern_sorted_by_timestamp(self) -> None:
        """Test that results are sorted by timestamp (most recent first)."""
        store = DecisionStore()
        pattern_id = str(uuid.uuid4())

        # Store decisions with slight delays to ensure different timestamps
        decision_ids = []
        for i in range(3):
            decision_id = store.store_decision(
                session_id=str(uuid.uuid4()),
                task=f"Task {i}",
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
            decision_ids.append(decision_id)
            import time

            time.sleep(0.01)  # Small delay to ensure different timestamps

        results = store.get_decisions_for_pattern(pattern_id)
        assert len(results) == 3

        # Verify sorted by timestamp (most recent first)
        timestamps = [r["timestamp"] for r in results]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_get_decisions_for_pattern_preserves_all_fields(self) -> None:
        """Test that all decision fields are preserved."""
        store = DecisionStore()
        session_id = str(uuid.uuid4())
        pattern_id = str(uuid.uuid4())
        alternatives = [
            {
                "pattern_id": str(uuid.uuid4()),
                "name": "Alt 1",
                "confidence": 0.7,
                "why_rejected": "Lower confidence",
            }
        ]
        counterfactual = {
            "chosen_cost": 100.0,
            "alternative_costs": [150.0],
            "default_cost": 300.0,
            "counterfactual_type": "estimated",
        }
        outcome = {
            "success": True,
            "primary_outcome": "Bug fixed",
            "violations_introduced": 0,
            "token_efficiency": 0.95,
            "rework_needed": False,
        }

        decision_id = store.store_decision(
            session_id=session_id,
            task="Fix authentication",
            chosen_pattern=pattern_id,
            pattern_confidence=0.85,
            alternatives_considered=alternatives,
            counterfactual=counterfactual,
            outcome=outcome,
        )

        results = store.get_decisions_for_pattern(pattern_id)
        assert len(results) == 1

        decision = results[0]
        assert decision["decision_id"] == decision_id
        assert decision["session_id"] == session_id
        assert decision["task"] == "Fix authentication"
        assert decision["chosen_pattern"] == pattern_id
        assert decision["pattern_confidence"] == 0.85
        assert decision["alternatives_considered"] == alternatives
        assert decision["counterfactual"] == counterfactual
        assert decision["outcome"] == outcome

    def test_get_decisions_for_pattern_with_and_without_outcome(self) -> None:
        """Test retrieving decisions with and without outcome information."""
        store = DecisionStore()
        pattern_id = str(uuid.uuid4())

        # Decision without outcome
        decision_id_1 = store.store_decision(
            session_id=str(uuid.uuid4()),
            task="Task 1",
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

        # Decision with outcome
        decision_id_2 = store.store_decision(
            session_id=str(uuid.uuid4()),
            task="Task 2",
            chosen_pattern=pattern_id,
            pattern_confidence=0.85,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 110.0,
                "alternative_costs": [],
                "default_cost": 310.0,
                "counterfactual_type": "measured",
            },
            outcome={
                "success": True,
                "primary_outcome": "Success",
                "violations_introduced": 0,
                "token_efficiency": 0.9,
                "rework_needed": False,
            },
        )

        results = store.get_decisions_for_pattern(pattern_id)
        assert len(results) == 2

        # Find each decision
        decision_1 = next(d for d in results if d["decision_id"] == decision_id_1)
        decision_2 = next(d for d in results if d["decision_id"] == decision_id_2)

        assert decision_1["outcome"] is None
        assert decision_2["outcome"] is not None
        assert decision_2["outcome"]["success"] is True

    def test_get_decisions_for_pattern_handles_error_gracefully(self) -> None:
        """Test that errors are handled gracefully."""
        store = DecisionStore()

        # Should return empty list, not raise exception
        results = store.get_decisions_for_pattern("")
        assert isinstance(results, list)
        assert len(results) == 0
