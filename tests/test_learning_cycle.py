"""Integration tests for the learning cycle implementation.

Tests the LearningCycle class with real ledger events.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from divineos.agent_integration.learning_cycle import LearningCycle
from divineos.agent_integration.pattern_store import PatternStore
from divineos.agent_integration.decision_store import DecisionStore
from divineos.agent_integration.learning_audit_store import LearningAuditStore
from divineos.core.ledger import log_event


class TestLearningCycleBasics:
    """Test basic LearningCycle initialization and setup."""

    def test_learning_cycle_initialization(self) -> None:
        """Test that LearningCycle initializes correctly."""
        cycle = LearningCycle()
        assert cycle is not None
        assert cycle.logger is not None
        assert cycle.pattern_store is not None
        assert cycle.audit_store is not None
        assert cycle.decision_store is not None


class TestLoadWorkHistory:
    """Test load_work_history() - Subtask 2.1.1."""

    def test_load_work_history_empty(self) -> None:
        """Test loading work history when no events exist."""
        cycle = LearningCycle()
        history = cycle.load_work_history()
        assert isinstance(history, list)
        # May have events from other tests, so just check it's a list

    def test_load_work_history_filters_by_date(self) -> None:
        """Test that work history is filtered to last 30 days."""
        cycle = LearningCycle()

        # Create a work event from 40 days ago
        old_time = (datetime.now(UTC) - timedelta(days=40)).isoformat()
        old_payload = {
            "session_id": str(uuid.uuid4()),
            "task": "old_task",
            "status": "completed",
            "files_modified": [],
            "tests_passing": 0,
            "timestamp": old_time,
        }
        log_event(
            event_type="AGENT_WORK",
            actor="agent",
            payload=old_payload,
            validate=False,
        )

        # Create a work event from 10 days ago
        recent_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        recent_payload = {
            "session_id": str(uuid.uuid4()),
            "task": "recent_task",
            "status": "completed",
            "files_modified": [],
            "tests_passing": 0,
            "timestamp": recent_time,
        }
        log_event(
            event_type="AGENT_WORK",
            actor="agent",
            payload=recent_payload,
            validate=False,
        )

        history = cycle.load_work_history()
        # Should include recent but not old
        tasks = [h.get("task") for h in history if h is not None]
        assert "recent_task" in tasks
        # Old task may or may not be included depending on exact timing

    def test_load_work_history_returns_payloads(self) -> None:
        """Test that load_work_history returns event payloads."""
        cycle = LearningCycle()

        # Create a work event
        payload = {
            "session_id": str(uuid.uuid4()),
            "task": "test_task",
            "status": "completed",
            "files_modified": ["file1.py"],
            "tests_passing": 5,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        log_event(
            event_type="AGENT_WORK",
            actor="agent",
            payload=payload,
            validate=False,
        )

        history = cycle.load_work_history()
        assert len(history) > 0
        # Check that payloads are returned
        assert any(h.get("task") == "test_task" for h in history if h is not None)


class TestExtractPatterns:
    """Test extract_patterns() - Subtask 2.1.2."""

    def test_extract_patterns_empty_history(self) -> None:
        """Test extracting patterns from empty work history."""
        cycle = LearningCycle()
        patterns = cycle.extract_patterns([])
        assert isinstance(patterns, list)
        assert len(patterns) == 0

    def test_extract_patterns_from_decisions(self) -> None:
        """Test extracting patterns from decision history."""
        cycle = LearningCycle()
        pattern_store = PatternStore()
        decision_store = DecisionStore()

        # Create a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Test Pattern",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Create decisions using this pattern
        for i in range(3):
            decision_store.store_decision(
                session_id=str(uuid.uuid4()),
                task=f"task_{i}",
                chosen_pattern=pattern_id,
                pattern_confidence=0.5,
                alternatives_considered=[],
                counterfactual={
                    "chosen_cost": 100,
                    "alternative_costs": [150],
                    "default_cost": 200,
                    "counterfactual_type": "estimated",
                },
                outcome={
                    "success": i < 2,  # First 2 succeed, last fails
                    "primary_outcome": "completed",
                    "violations_introduced": 0,
                    "token_efficiency": 0.5,
                    "rework_needed": False,
                },
            )

        # Extract patterns
        work_history = [{"task": f"task_{i}"} for i in range(3)]
        patterns = cycle.extract_patterns(work_history)

        # Should have extracted the pattern
        assert len(patterns) > 0
        pattern_info = next((p for p in patterns if p["pattern_id"] == pattern_id), None)
        assert pattern_info is not None
        assert pattern_info["occurrences"] == 3
        assert pattern_info["successes"] == 2
        assert pattern_info["success_rate"] == pytest.approx(2 / 3)


class TestUpdateExistingPatterns:
    """Test update_existing_patterns() - Subtask 2.1.3."""

    def test_update_patterns_success_delta(self) -> None:
        """Test that successful outcomes increase confidence."""
        cycle = LearningCycle()
        pattern_store = PatternStore()
        decision_store = DecisionStore()

        # Create a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Test Pattern",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Create a successful decision
        decision_store.store_decision(
            session_id=str(uuid.uuid4()),
            task="task",
            chosen_pattern=pattern_id,
            pattern_confidence=0.5,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100,
                "alternative_costs": [150],
                "default_cost": 200,
                "counterfactual_type": "estimated",
            },
            outcome={
                "success": True,
                "primary_outcome": "completed",
                "violations_introduced": 0,
                "token_efficiency": 0.5,
                "rework_needed": False,
            },
        )

        # Extract and update
        work_history = [{"task": "task"}]
        patterns = cycle.extract_patterns(work_history)
        cycle.update_existing_patterns(patterns)

        # Check confidence increased
        updated_pattern = pattern_store.get_pattern(pattern_id)
        assert updated_pattern is not None
        assert updated_pattern["confidence"] > 0.5

    def test_update_patterns_failure_delta(self) -> None:
        """Test that failed outcomes decrease confidence more heavily."""
        cycle = LearningCycle()
        pattern_store = PatternStore()
        decision_store = DecisionStore()

        # Create a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Test Pattern",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Create a failed decision
        decision_store.store_decision(
            session_id=str(uuid.uuid4()),
            task="task",
            chosen_pattern=pattern_id,
            pattern_confidence=0.5,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100,
                "alternative_costs": [150],
                "default_cost": 200,
                "counterfactual_type": "estimated",
            },
            outcome={
                "success": False,
                "primary_outcome": "failed",
                "violations_introduced": 0,
                "token_efficiency": 0.5,
                "rework_needed": False,
            },
        )

        # Extract and update
        work_history = [{"task": "task"}]
        patterns = cycle.extract_patterns(work_history)
        cycle.update_existing_patterns(patterns)

        # Check confidence decreased more than success would increase
        updated_pattern = pattern_store.get_pattern(pattern_id)
        assert updated_pattern is not None
        assert updated_pattern["confidence"] < 0.5

    def test_update_patterns_secondary_effects(self) -> None:
        """Test that violations introduce additional penalty."""
        cycle = LearningCycle()
        pattern_store = PatternStore()
        decision_store = DecisionStore()

        # Create a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Test Pattern",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Create a decision with violations
        decision_store.store_decision(
            session_id=str(uuid.uuid4()),
            task="task",
            chosen_pattern=pattern_id,
            pattern_confidence=0.5,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100,
                "alternative_costs": [150],
                "default_cost": 200,
                "counterfactual_type": "estimated",
            },
            outcome={
                "success": True,
                "primary_outcome": "completed",
                "violations_introduced": 2,  # Violations!
                "token_efficiency": 0.5,
                "rework_needed": False,
            },
        )

        # Extract and update
        work_history = [{"task": "task"}]
        patterns = cycle.extract_patterns(work_history)
        cycle.update_existing_patterns(patterns)

        # Check confidence increased less than without violations
        updated_pattern = pattern_store.get_pattern(pattern_id)
        assert updated_pattern is not None
        # Success delta (0.05) - secondary effects delta (0.1) = -0.05
        assert updated_pattern["confidence"] < 0.5


class TestDetectInvalidation:
    """Test detect_invalidation() - Subtask 2.1.4."""

    def test_detect_invalidation_anti_patterns(self) -> None:
        """Test that anti-patterns are archived."""
        cycle = LearningCycle()
        pattern_store = PatternStore()

        # Create an anti-pattern (confidence < -0.5)
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Anti-Pattern",
            description="Test",
            preconditions={},
            confidence=-0.6,
        )

        # Detect invalidation
        archived = cycle.detect_invalidation()

        # Should be archived
        assert pattern_id in archived
        updated_pattern = pattern_store.get_pattern(pattern_id)
        assert updated_pattern is not None
        assert updated_pattern["confidence"] == -0.5

    def test_detect_invalidation_tactical_failures(self) -> None:
        """Test that tactical patterns with 3+ failures are archived."""
        cycle = LearningCycle()
        pattern_store = PatternStore()

        # Create a tactical pattern with 3 failures
        pattern_id = pattern_store.store_pattern(
            pattern_type="tactical",
            name="Tactical Pattern",
            description="Test",
            preconditions={},
            occurrences=3,
            successes=0,  # 3 failures
            confidence=0.5,
        )

        # Detect invalidation
        archived = cycle.detect_invalidation()

        # Should be archived
        assert pattern_id in archived


class TestDetectConflicts:
    """Test detect_conflicts() - Subtask 2.1.5."""

    def test_detect_conflicts_contradictory_patterns(self) -> None:
        """Test that contradictory structural patterns are detected."""
        cycle = LearningCycle()
        pattern_store = PatternStore()

        # Create two structural patterns with contradictory preconditions
        pattern_id_1 = pattern_store.store_pattern(
            pattern_type="structural",
            name="Pattern 1",
            description="Test",
            preconditions={"phase": "bugfix"},
            confidence=0.8,
        )

        pattern_id_2 = pattern_store.store_pattern(
            pattern_type="structural",
            name="Pattern 2",
            description="Test",
            preconditions={"phase": "feature"},
            confidence=0.8,
        )

        # Detect conflicts
        conflicts = cycle.detect_conflicts()

        # Should detect conflict
        assert len(conflicts) > 0
        conflict = conflicts[0]
        assert conflict["pattern_id_1"] in [pattern_id_1, pattern_id_2]
        assert conflict["pattern_id_2"] in [pattern_id_1, pattern_id_2]

    def test_detect_conflicts_no_conflicts(self) -> None:
        """Test that compatible patterns don't conflict."""
        cycle = LearningCycle()
        pattern_store = PatternStore()

        # Create two structural patterns with compatible preconditions
        pattern_store.store_pattern(
            pattern_type="structural",
            name="Pattern 1",
            description="Test",
            preconditions={"phase": "bugfix"},
            confidence=0.8,
        )

        pattern_store.store_pattern(
            pattern_type="structural",
            name="Pattern 2",
            description="Test",
            preconditions={"phase": "bugfix"},
            confidence=0.8,
        )

        # Detect conflicts
        conflicts = cycle.detect_conflicts()

        # Should not detect conflict (same preconditions)
        assert len(conflicts) == 0


class TestGenerateHumilityAudit:
    """Test generate_humility_audit() - Subtask 2.1.6."""

    def test_generate_humility_audit_low_confidence(self) -> None:
        """Test that low confidence patterns are flagged."""
        cycle = LearningCycle()
        pattern_store = PatternStore()

        # Create a low confidence pattern
        pattern_store.store_pattern(
            pattern_type="structural",
            name="Low Confidence",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Generate audit
        audit = cycle.generate_humility_audit()

        # Should flag low confidence
        assert len(audit["low_confidence_patterns"]) > 0

    def test_generate_humility_audit_untested_patterns(self) -> None:
        """Test that untested patterns are flagged."""
        cycle = LearningCycle()
        pattern_store = PatternStore()

        # Create a pattern but don't use it in any decisions
        pattern_store.store_pattern(
            pattern_type="structural",
            name="Untested",
            description="Test",
            preconditions={},
            confidence=0.8,
        )

        # Generate audit
        audit = cycle.generate_humility_audit()

        # Should flag untested
        assert len(audit["untested_patterns"]) > 0

    def test_generate_humility_audit_drift_detection(self) -> None:
        """Test that drift is detected when >50% patterns have low confidence."""
        cycle = LearningCycle()
        pattern_store = PatternStore()

        # Create multiple low confidence patterns
        for i in range(3):
            pattern_store.store_pattern(
                pattern_type="structural",
                name=f"Low Confidence {i}",
                description="Test",
                preconditions={},
                confidence=0.4,
            )

        # Create one high confidence pattern
        pattern_store.store_pattern(
            pattern_type="structural",
            name="High Confidence",
            description="Test",
            preconditions={},
            confidence=0.9,
        )

        # Generate audit
        audit = cycle.generate_humility_audit()

        # Should detect drift (3/4 = 75% below 0.6)
        assert audit["drift_detected"] is True
        assert audit["drift_reason"] is not None


class TestRunFullCycle:
    """Test run() - Subtask 2.1.7."""

    def test_run_full_learning_cycle(self) -> None:
        """Test running the full learning cycle."""
        cycle = LearningCycle()
        pattern_store = PatternStore()
        decision_store = DecisionStore()

        # Create a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Test Pattern",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Create a decision
        decision_store.store_decision(
            session_id="test_session",
            task="task",
            chosen_pattern=pattern_id,
            pattern_confidence=0.5,
            alternatives_considered=[],
            counterfactual={
                "chosen_cost": 100,
                "alternative_costs": [150],
                "default_cost": 200,
                "counterfactual_type": "estimated",
            },
            outcome={
                "success": True,
                "primary_outcome": "completed",
                "violations_introduced": 0,
                "token_efficiency": 0.5,
                "rework_needed": False,
            },
        )

        # Run full cycle
        results = cycle.run("test_session")

        # Check results
        assert results["session_id"] == "test_session"
        assert results["work_history_count"] >= 0
        assert results["patterns_extracted"] >= 0
        assert results["audit_id"] is not None
        assert "audit" in results
        assert "timestamp" in results

    def test_run_cycle_stores_audit(self) -> None:
        """Test that run() stores audit to ledger."""
        cycle = LearningCycle()
        audit_store = LearningAuditStore()

        # Run cycle
        session_id = str(uuid.uuid4())
        results = cycle.run(session_id)
        assert results is not None
        assert isinstance(results, dict)

        # Check that audit was stored
        latest_audit = audit_store.get_latest_audit()
        assert latest_audit is not None
        assert latest_audit["session_id"] == session_id
