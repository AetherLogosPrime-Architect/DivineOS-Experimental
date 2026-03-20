"""Integration tests for AgentMemoryMonitor with learning cycle and pattern recommender.

Tests cover Task 4 subtasks:
- 4.1.1 run_learning_cycle() - call LearningCycle at session end
- 4.1.2 get_recommendation() - call PatternRecommender for new work
- 4.1.3 record_work_outcome() - measure outcomes after work completes
- 4.2 Update end_session() to trigger learning cycle
- 4.3 Integration tests (memory monitor + learning cycle + ledger)
"""

import uuid
from datetime import UTC, datetime


from divineos.agent_integration.memory_monitor import AgentMemoryMonitor
from divineos.agent_integration.pattern_store import PatternStore
from divineos.agent_integration.decision_store import DecisionStore
from divineos.agent_integration.learning_audit_store import LearningAuditStore
from divineos.core.ledger import log_event, get_events


class TestRunLearningCycle:
    """Test run_learning_cycle() - Subtask 4.1.1."""

    def test_run_learning_cycle_returns_results(self) -> None:
        """Test that run_learning_cycle returns results with audit_id."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        results = monitor.run_learning_cycle()

        assert results is not None
        assert "session_id" in results
        assert results["session_id"] == session_id
        assert "audit_id" in results
        assert "patterns_extracted" in results

    def test_run_learning_cycle_stores_audit(self) -> None:
        """Test that run_learning_cycle stores audit to ledger."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        monitor.run_learning_cycle()

        # Check that audit was stored
        audit_store = LearningAuditStore()
        latest_audit = audit_store.get_latest_audit()

        assert latest_audit is not None
        assert latest_audit["session_id"] == session_id

    def test_run_learning_cycle_with_work_history(self) -> None:
        """Test learning cycle with actual work history."""
        session_id = str(uuid.uuid4())
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
            session_id=session_id,
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

        # Run learning cycle
        monitor = AgentMemoryMonitor(session_id)
        results = monitor.run_learning_cycle()

        assert results["patterns_extracted"] >= 0
        assert results["audit_id"] is not None

    def test_run_learning_cycle_handles_errors(self) -> None:
        """Test that run_learning_cycle handles errors gracefully."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        # This should not raise an exception even if something goes wrong
        results = monitor.run_learning_cycle()

        assert results is not None
        assert "session_id" in results


class TestGetRecommendation:
    """Test get_recommendation() - Subtask 4.1.2."""

    def test_get_recommendation_returns_recommendation(self) -> None:
        """Test that get_recommendation returns a recommendation."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        context = {"phase": "bugfix", "token_budget": 150000}
        recommendation = monitor.get_recommendation(context)

        assert recommendation is not None
        assert "pattern_id" in recommendation
        assert "pattern_name" in recommendation
        assert "confidence" in recommendation
        assert "explanation" in recommendation

    def test_get_recommendation_with_matching_pattern(self) -> None:
        """Test get_recommendation with a matching pattern."""
        session_id = str(uuid.uuid4())
        pattern_store = PatternStore()

        # Create a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Bugfix Pattern",
            description="Pattern for bugfix phase",
            preconditions={"phase": "bugfix"},
            confidence=0.85,
        )

        monitor = AgentMemoryMonitor(session_id)
        context = {"phase": "bugfix", "token_budget": 150000}
        recommendation = monitor.get_recommendation(context)

        assert recommendation is not None
        assert recommendation["pattern_id"] == pattern_id
        assert recommendation["confidence"] == 0.85

    def test_get_recommendation_fallback_no_patterns(self) -> None:
        """Test get_recommendation returns fallback when no patterns match."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        context = {"phase": "unknown_phase", "token_budget": 50000}
        recommendation = monitor.get_recommendation(context)

        assert recommendation is not None
        # Should return fallback recommendation
        assert recommendation["confidence"] <= 0.3

    def test_get_recommendation_includes_uncertainty(self) -> None:
        """Test that recommendation includes uncertainty statement."""
        session_id = str(uuid.uuid4())
        pattern_store = PatternStore()

        # Create a pattern with no preconditions (matches any context)
        pattern_store.store_pattern(
            pattern_type="structural",
            name="Test Pattern",
            description="Test",
            preconditions={},
            confidence=0.75,
        )

        monitor = AgentMemoryMonitor(session_id)
        # Provide context that will match the pattern
        context = {"phase": "bugfix"}
        recommendation = monitor.get_recommendation(context)

        assert "uncertainty_statement" in recommendation
        # Should have uncertainty statement with confidence level
        assert (
            "75%" in recommendation["uncertainty_statement"]
            or "could be wrong" in recommendation["uncertainty_statement"]
        )

    def test_get_recommendation_includes_failure_modes(self) -> None:
        """Test that recommendation includes failure modes."""
        session_id = str(uuid.uuid4())
        pattern_store = PatternStore()

        # Create a pattern
        pattern_store.store_pattern(
            pattern_type="structural",
            name="Test Pattern",
            description="Test",
            preconditions={},
            confidence=0.8,
        )

        monitor = AgentMemoryMonitor(session_id)
        context = {}
        recommendation = monitor.get_recommendation(context)

        assert "failure_modes" in recommendation
        assert isinstance(recommendation["failure_modes"], list)

    def test_get_recommendation_handles_errors(self) -> None:
        """Test that get_recommendation handles errors gracefully."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        # This should not raise an exception
        recommendation = monitor.get_recommendation({})

        assert recommendation is not None
        assert "pattern_id" in recommendation


class TestRecordWorkOutcome:
    """Test record_work_outcome() - Subtask 4.1.3."""

    def test_record_work_outcome_stores_event(self) -> None:
        """Test that record_work_outcome stores event to ledger."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        pattern_id = str(uuid.uuid4())
        event_id = monitor.record_work_outcome(
            task="Fix bug",
            pattern_id=pattern_id,
            success=True,
            violations_introduced=0,
            token_efficiency=0.8,
            rework_needed=False,
        )

        assert event_id is not None

        # Verify event was stored
        events = get_events(event_type="AGENT_WORK_OUTCOME", actor="agent")
        outcome_events = [e for e in events if e.get("payload", {}).get("session_id") == session_id]
        assert len(outcome_events) > 0

    def test_record_work_outcome_success(self) -> None:
        """Test recording a successful work outcome."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        pattern_id = str(uuid.uuid4())
        event_id = monitor.record_work_outcome(
            task="Fix authentication bug",
            pattern_id=pattern_id,
            success=True,
            violations_introduced=0,
            token_efficiency=0.85,
            rework_needed=False,
        )

        assert event_id is not None

        # Verify outcome details
        events = get_events(event_type="AGENT_WORK_OUTCOME", actor="agent")
        outcome_event = next((e for e in events if e.get("event_id") == event_id), None)
        assert outcome_event is not None
        payload = outcome_event.get("payload", {})
        assert payload["outcome"]["success"] is True
        assert payload["outcome"]["violations_introduced"] == 0

    def test_record_work_outcome_failure(self) -> None:
        """Test recording a failed work outcome."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        pattern_id = str(uuid.uuid4())
        event_id = monitor.record_work_outcome(
            task="Fix bug",
            pattern_id=pattern_id,
            success=False,
            violations_introduced=2,
            token_efficiency=0.5,
            rework_needed=True,
        )

        assert event_id is not None

        # Verify outcome details
        events = get_events(event_type="AGENT_WORK_OUTCOME", actor="agent")
        outcome_event = next((e for e in events if e.get("event_id") == event_id), None)
        assert outcome_event is not None
        payload = outcome_event.get("payload", {})
        assert payload["outcome"]["success"] is False
        assert payload["outcome"]["violations_introduced"] == 2
        assert payload["outcome"]["rework_needed"] is True

    def test_record_work_outcome_with_violations(self) -> None:
        """Test recording outcome with violations introduced."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        pattern_id = str(uuid.uuid4())
        event_id = monitor.record_work_outcome(
            task="Refactor code",
            pattern_id=pattern_id,
            success=True,
            violations_introduced=3,
            token_efficiency=0.7,
            rework_needed=False,
        )

        assert event_id is not None

        # Verify violations were recorded
        events = get_events(event_type="AGENT_WORK_OUTCOME", actor="agent")
        outcome_event = next((e for e in events if e.get("event_id") == event_id), None)
        assert outcome_event is not None
        payload = outcome_event.get("payload", {})
        assert payload["outcome"]["violations_introduced"] == 3


class TestEndSessionWithLearningCycle:
    """Test end_session() with learning cycle - Subtask 4.2."""

    def test_end_session_triggers_learning_cycle(self) -> None:
        """Test that end_session triggers learning cycle."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        # End session
        event_id = monitor.end_session(summary="Completed bugfix work", final_status="completed")

        assert event_id is not None

        # Verify session end event was stored
        events = get_events(event_type="AGENT_SESSION_END", actor="agent")
        session_end_events = [
            e for e in events if e.get("payload", {}).get("session_id") == session_id
        ]
        assert len(session_end_events) > 0

        # Verify learning cycle results are included
        session_end_event = session_end_events[0]
        payload = session_end_event.get("payload", {})
        assert "learning_cycle_results" in payload
        assert payload["learning_cycle_results"] is not None

    def test_end_session_stores_final_status(self) -> None:
        """Test that end_session stores final status."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        event_id = monitor.end_session(summary="Work completed", final_status="completed")

        assert event_id is not None

        # Verify final status
        events = get_events(event_type="AGENT_SESSION_END", actor="agent")
        session_end_event = next((e for e in events if e.get("event_id") == event_id), None)
        assert session_end_event is not None
        payload = session_end_event.get("payload", {})
        assert payload["final_status"] == "completed"

    def test_end_session_with_failed_status(self) -> None:
        """Test end_session with failed status."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        event_id = monitor.end_session(summary="Work failed", final_status="failed")

        assert event_id is not None

        # Verify failed status
        events = get_events(event_type="AGENT_SESSION_END", actor="agent")
        session_end_event = next((e for e in events if e.get("event_id") == event_id), None)
        assert session_end_event is not None
        payload = session_end_event.get("payload", {})
        assert payload["final_status"] == "failed"


class TestMemoryMonitorIntegration:
    """Integration tests for full memory monitor workflow - Subtask 4.3."""

    def test_full_workflow_recommendation_to_outcome(self) -> None:
        """Test full workflow: get recommendation, do work, record outcome."""
        session_id = str(uuid.uuid4())
        pattern_store = PatternStore()
        monitor = AgentMemoryMonitor(session_id)

        # Create a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Bugfix Pattern",
            description="Pattern for bugfix work",
            preconditions={"phase": "bugfix"},
            confidence=0.8,
        )

        # Get recommendation
        context = {"phase": "bugfix", "token_budget": 150000}
        recommendation = monitor.get_recommendation(context)

        assert recommendation["pattern_id"] == pattern_id

        # Do work and record outcome
        outcome_event_id = monitor.record_work_outcome(
            task="Fix authentication bug",
            pattern_id=pattern_id,
            success=True,
            violations_introduced=0,
            token_efficiency=0.85,
            rework_needed=False,
        )

        assert outcome_event_id is not None

        # End session (triggers learning cycle)
        session_end_event_id = monitor.end_session(
            summary="Completed bugfix", final_status="completed"
        )

        assert session_end_event_id is not None

        # Verify all events were stored
        events = get_events(event_type="AGENT_WORK_OUTCOME", actor="agent")
        outcome_events = [e for e in events if e.get("payload", {}).get("session_id") == session_id]
        assert len(outcome_events) > 0

    def test_multiple_recommendations_in_session(self) -> None:
        """Test getting multiple recommendations in a single session."""
        session_id = str(uuid.uuid4())
        pattern_store = PatternStore()
        monitor = AgentMemoryMonitor(session_id)

        # Create patterns for different phases
        bugfix_pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Bugfix Pattern",
            description="For bugfix phase",
            preconditions={"phase": "bugfix"},
            confidence=0.85,
        )

        feature_pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Feature Pattern",
            description="For feature phase",
            preconditions={"phase": "feature"},
            confidence=0.75,
        )

        # Get recommendations for different contexts
        bugfix_rec = monitor.get_recommendation({"phase": "bugfix"})
        assert bugfix_rec["pattern_id"] == bugfix_pattern_id

        feature_rec = monitor.get_recommendation({"phase": "feature"})
        assert feature_rec["pattern_id"] == feature_pattern_id

    def test_learning_cycle_updates_pattern_confidence(self) -> None:
        """Test that learning cycle updates pattern confidence based on outcomes."""
        session_id = str(uuid.uuid4())
        pattern_store = PatternStore()
        decision_store = DecisionStore()
        monitor = AgentMemoryMonitor(session_id)

        # Create a pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Test Pattern",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Create a work event
        work_payload = {
            "session_id": session_id,
            "task": "task",
            "status": "completed",
            "files_modified": ["file.py"],
            "tests_passing": 5,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        log_event(
            event_type="AGENT_WORK",
            actor="agent",
            payload=work_payload,
            validate=False,
        )

        # Create a successful decision
        decision_store.store_decision(
            session_id=session_id,
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
                "token_efficiency": 0.8,
                "rework_needed": False,
            },
        )

        # Run learning cycle
        monitor.run_learning_cycle()

        # Pattern confidence should have been updated
        updated_pattern = pattern_store.get_pattern(pattern_id)
        assert updated_pattern is not None
        # Success should increase confidence
        assert updated_pattern["confidence"] > 0.5

    def test_humility_audit_loaded_before_recommendation(self) -> None:
        """Test that humility audit is loaded before generating recommendation."""
        session_id = str(uuid.uuid4())
        pattern_store = PatternStore()
        monitor = AgentMemoryMonitor(session_id)

        # Create a low-confidence pattern
        pattern_store.store_pattern(
            pattern_type="structural",
            name="Low Confidence Pattern",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Run learning cycle to generate audit
        monitor.run_learning_cycle()

        # Get recommendation (should load audit)
        recommendation = monitor.get_recommendation({})

        # Recommendation should be generated (audit doesn't prevent it)
        assert recommendation is not None
        assert "pattern_id" in recommendation

    def test_session_end_includes_token_usage(self) -> None:
        """Test that session end includes final token usage."""
        session_id = str(uuid.uuid4())
        monitor = AgentMemoryMonitor(session_id)

        # Update token usage
        monitor.update_token_usage(150000)

        # End session
        event_id = monitor.end_session(summary="Work completed", final_status="completed")

        # Verify token usage is recorded
        events = get_events(event_type="AGENT_SESSION_END", actor="agent")
        session_end_event = next((e for e in events if e.get("event_id") == event_id), None)
        assert session_end_event is not None
        payload = session_end_event.get("payload", {})
        assert payload["final_token_usage"] == 150000
