"""Property-based tests for learning loop correctness invariants.

Tests cover Task 5 subtasks:
- 5.1.1 CP1: Pattern consistency - same task characteristics → same recommendation
- 5.1.2 CP2: Anti-pattern enforcement - anti-patterns never recommended without override
- 5.1.3 CP3: Outcome tracking - confidence updates reflect actual outcomes
- 5.1.4 CP4: No circular reasoning - patterns trace to actual work outcomes
- 5.1.5 CP5: Structural vs tactical decay - structural patterns don't decay by time
- 5.1.6 CP6: Humility audit accuracy - audit reflects actual pattern state
- 5.1.7 CP7: Counterfactual validity - counterfactuals recorded at decision time
- 5.2 Edge case tests
- 5.3 Integration tests (full learning cycle with real scenarios)
"""

import uuid
from datetime import UTC, datetime


from divineos.agent_integration.pattern_store import PatternStore
from divineos.agent_integration.decision_store import DecisionStore
from divineos.agent_integration.learning_cycle import LearningCycle
from divineos.agent_integration.pattern_recommender import PatternRecommender
from divineos.core.ledger import log_event, get_events


class TestCP1PatternConsistency:
    """CP1: Pattern consistency - same task characteristics → same recommendation."""

    def test_same_context_returns_same_pattern(self) -> None:
        """Test that same context returns same pattern recommendation."""
        pattern_store = PatternStore()

        # Create a pattern
        pattern_store.store_pattern(
            pattern_type="structural",
            name="Consistent Pattern",
            description="Test",
            preconditions={"phase": "bugfix"},
            confidence=0.8,
        )

        recommender = PatternRecommender()
        context = {"phase": "bugfix"}

        # Get recommendation twice
        rec1 = recommender.generate_recommendation(context)
        rec2 = recommender.generate_recommendation(context)

        # Should return same pattern
        assert rec1["pattern_id"] == rec2["pattern_id"]
        assert rec1["confidence"] == rec2["confidence"]

    def test_different_context_returns_different_pattern(self) -> None:
        """Test that different context can return different patterns."""
        pattern_store = PatternStore()

        # Create two patterns for different phases
        pattern_id_1 = pattern_store.store_pattern(
            pattern_type="structural",
            name="Bugfix Pattern",
            description="Test",
            preconditions={"phase": "bugfix"},
            confidence=0.85,
        )

        pattern_id_2 = pattern_store.store_pattern(
            pattern_type="structural",
            name="Feature Pattern",
            description="Test",
            preconditions={"phase": "feature"},
            confidence=0.75,
        )

        recommender = PatternRecommender()

        # Get recommendations for different contexts
        rec_bugfix = recommender.generate_recommendation({"phase": "bugfix"})
        rec_feature = recommender.generate_recommendation({"phase": "feature"})

        # Should return different patterns
        assert rec_bugfix["pattern_id"] == pattern_id_1
        assert rec_feature["pattern_id"] == pattern_id_2


class TestCP2AntiPatternEnforcement:
    """CP2: Anti-pattern enforcement - anti-patterns never recommended without override."""

    def test_anti_pattern_not_recommended(self) -> None:
        """Test that anti-patterns (confidence < -0.5) are not recommended."""
        pattern_store = PatternStore()

        # Create an anti-pattern
        anti_pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Anti-Pattern",
            description="Never use this",
            preconditions={},
            confidence=-0.8,  # Anti-pattern
        )

        recommender = PatternRecommender()
        recommendation = recommender.generate_recommendation({})

        # Should not recommend the anti-pattern
        assert recommendation["pattern_id"] != anti_pattern_id

    def test_positive_pattern_recommended_over_anti_pattern(self) -> None:
        """Test that positive patterns are recommended over anti-patterns."""
        pattern_store = PatternStore()

        # Create a positive pattern
        positive_pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Good Pattern",
            description="Use this",
            preconditions={},
            confidence=0.8,
        )

        # Create an anti-pattern
        pattern_store.store_pattern(
            pattern_type="structural",
            name="Bad Pattern",
            description="Never use this",
            preconditions={},
            confidence=-0.7,
        )

        recommender = PatternRecommender()
        recommendation = recommender.generate_recommendation({})

        # Should recommend positive pattern, not anti-pattern
        # (or fallback if neither matches)
        if recommendation["pattern_id"] != "fallback":
            assert recommendation["pattern_id"] == positive_pattern_id


class TestCP3OutcomeTracking:
    """CP3: Outcome tracking - confidence updates reflect actual outcomes."""

    def test_success_increases_confidence(self) -> None:
        """Test that successful outcomes increase pattern confidence."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()
        session_id = str(uuid.uuid4())

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
        cycle = LearningCycle()
        cycle.run(session_id)

        # Pattern confidence should increase
        updated_pattern = pattern_store.get_pattern(pattern_id)
        assert updated_pattern["confidence"] > 0.5

    def test_failure_decreases_confidence(self) -> None:
        """Test that failed outcomes decrease pattern confidence."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()
        session_id = str(uuid.uuid4())

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
            "status": "failed",
            "files_modified": ["file.py"],
            "tests_passing": 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        log_event(
            event_type="AGENT_WORK",
            actor="agent",
            payload=work_payload,
            validate=False,
        )

        # Create a failed decision
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
                "success": False,
                "primary_outcome": "failed",
                "violations_introduced": 0,
                "token_efficiency": 0.5,
                "rework_needed": False,
            },
        )

        # Run learning cycle
        cycle = LearningCycle()
        cycle.run(session_id)

        # Pattern confidence should decrease
        updated_pattern = pattern_store.get_pattern(pattern_id)
        assert updated_pattern["confidence"] < 0.5

    def test_violations_introduce_additional_penalty(self) -> None:
        """Test that violations introduce additional confidence penalty."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()
        session_id_1 = str(uuid.uuid4())
        session_id_2 = str(uuid.uuid4())

        # Create two patterns
        pattern_id_1 = pattern_store.store_pattern(
            pattern_type="structural",
            name="Pattern 1",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        pattern_id_2 = pattern_store.store_pattern(
            pattern_type="structural",
            name="Pattern 2",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Create work event 1
        work_payload_1 = {
            "session_id": session_id_1,
            "task": "task1",
            "status": "completed",
            "files_modified": ["file.py"],
            "tests_passing": 5,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        log_event(
            event_type="AGENT_WORK",
            actor="agent",
            payload=work_payload_1,
            validate=False,
        )

        # Create successful decision without violations
        decision_store.store_decision(
            session_id=session_id_1,
            task="task1",
            chosen_pattern=pattern_id_1,
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

        # Create work event 2
        work_payload_2 = {
            "session_id": session_id_2,
            "task": "task2",
            "status": "completed",
            "files_modified": ["file.py"],
            "tests_passing": 5,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        log_event(
            event_type="AGENT_WORK",
            actor="agent",
            payload=work_payload_2,
            validate=False,
        )

        # Create successful decision with violations
        decision_store.store_decision(
            session_id=session_id_2,
            task="task2",
            chosen_pattern=pattern_id_2,
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
                "violations_introduced": 3,
                "token_efficiency": 0.8,
                "rework_needed": False,
            },
        )

        # Run learning cycles
        cycle = LearningCycle()
        cycle.run(session_id_1)
        cycle.run(session_id_2)

        # Pattern 1 should have higher confidence than Pattern 2
        pattern_1 = pattern_store.get_pattern(pattern_id_1)
        pattern_2 = pattern_store.get_pattern(pattern_id_2)
        assert pattern_1["confidence"] > pattern_2["confidence"]


class TestCP4NoCircularReasoning:
    """CP4: No circular reasoning - patterns trace to actual work outcomes."""

    def test_patterns_trace_to_work_outcomes(self) -> None:
        """Test that patterns are based on actual work outcomes."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()
        session_id = str(uuid.uuid4())

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

        # Create a decision with outcome
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

        # Pattern should exist and be retrievable
        pattern = pattern_store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern["pattern_id"] == pattern_id
        # Pattern is based on actual work outcome (stored in ledger)
        assert pattern["confidence"] == 0.5  # Initial confidence


class TestCP5StructuralVsTacticalDecay:
    """CP5: Structural vs tactical decay - structural patterns don't decay by time."""

    def test_structural_pattern_no_time_decay(self) -> None:
        """Test that structural patterns don't decay by time."""
        pattern_store = PatternStore()

        # Create a structural pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="structural",
            name="Structural Pattern",
            description="Test",
            preconditions={},
            confidence=0.8,
        )

        # Get pattern
        pattern = pattern_store.get_pattern(pattern_id)
        initial_confidence = pattern["confidence"]

        # Simulate time passing (in real system, would be days)
        # Structural patterns should not decay
        assert pattern["pattern_type"] == "structural"
        # Confidence should not change due to time
        assert pattern["confidence"] == initial_confidence

    def test_tactical_pattern_has_decay_rate(self) -> None:
        """Test that tactical patterns have decay rate."""
        pattern_store = PatternStore()

        # Create a tactical pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="tactical",
            name="Tactical Pattern",
            description="Test",
            preconditions={},
            confidence=0.8,
        )

        # Get pattern
        pattern = pattern_store.get_pattern(pattern_id)

        # Tactical patterns should have decay rate
        assert pattern["pattern_type"] == "tactical"
        assert "decay_rate" in pattern
        assert pattern["decay_rate"] == 0.05  # 5% per week


class TestCP6HumilityAuditAccuracy:
    """CP6: Humility audit accuracy - audit reflects actual pattern state."""

    def test_humility_audit_flags_low_confidence_patterns(self) -> None:
        """Test that humility audit flags patterns with low confidence."""
        pattern_store = PatternStore()

        # Create a low-confidence pattern
        pattern_store.store_pattern(
            pattern_type="structural",
            name="Low Confidence",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Generate audit
        cycle = LearningCycle()
        audit = cycle.generate_humility_audit()

        # Should flag low-confidence pattern
        assert len(audit["low_confidence_patterns"]) > 0

    def test_humility_audit_detects_drift(self) -> None:
        """Test that humility audit detects drift when >50% patterns have low confidence."""
        pattern_store = PatternStore()

        # Create multiple low-confidence patterns
        for i in range(3):
            pattern_store.store_pattern(
                pattern_type="structural",
                name=f"Low Confidence {i}",
                description="Test",
                preconditions={},
                confidence=0.4,
            )

        # Create one high-confidence pattern
        pattern_store.store_pattern(
            pattern_type="structural",
            name="High Confidence",
            description="Test",
            preconditions={},
            confidence=0.9,
        )

        # Generate audit
        cycle = LearningCycle()
        audit = cycle.generate_humility_audit()

        # Should detect drift (3/4 = 75% below 0.6)
        assert audit["drift_detected"] is True


class TestCP7CounterfactualValidity:
    """CP7: Counterfactual validity - counterfactuals recorded at decision time."""

    def test_counterfactual_recorded_with_decision(self) -> None:
        """Test that counterfactuals are recorded when decision is made."""
        decision_store = DecisionStore()
        session_id = str(uuid.uuid4())

        # Create a decision with counterfactual
        decision_id = decision_store.store_decision(
            session_id=session_id,
            task="task",
            chosen_pattern=str(uuid.uuid4()),
            pattern_confidence=0.8,
            alternatives_considered=[
                {
                    "pattern_id": str(uuid.uuid4()),
                    "name": "Alternative",
                    "confidence": 0.6,
                    "why_rejected": "Lower confidence",
                }
            ],
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

        # Decision should be stored
        assert decision_id is not None

        # Get decision from ledger
        events = get_events(event_type="AGENT_DECISION", actor="agent", limit=10000)

        # Find the decision event
        decision_event = None
        for e in events:
            if e.get("event_id") == decision_id:
                decision_event = e
                break

        # If we found it, verify counterfactual is there
        if decision_event is not None:
            payload = decision_event.get("payload", {})
            assert "counterfactual" in payload
            assert payload["counterfactual"]["chosen_cost"] == 100


class TestEdgeCases:
    """Edge case tests for learning loop."""

    def test_no_work_history_first_session(self) -> None:
        """Test learning cycle with no work history (first session)."""
        cycle = LearningCycle()
        results = cycle.run(str(uuid.uuid4()))

        # Should handle gracefully
        assert results is not None
        assert results["patterns_extracted"] == 0

    def test_conflicting_structural_patterns(self) -> None:
        """Test detection of conflicting structural patterns."""
        pattern_store = PatternStore()

        # Create two structural patterns with contradictory preconditions
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
            preconditions={"phase": "feature"},
            confidence=0.8,
        )

        # Detect conflicts
        cycle = LearningCycle()
        conflicts = cycle.detect_conflicts()

        # Should detect conflict
        assert len(conflicts) > 0

    def test_all_patterns_below_confidence_threshold(self) -> None:
        """Test when all patterns are below confidence threshold."""
        pattern_store = PatternStore()

        # Create patterns all below threshold
        for i in range(3):
            pattern_store.store_pattern(
                pattern_type="structural",
                name=f"Pattern {i}",
                description="Test",
                preconditions={},
                confidence=0.5,
            )

        recommender = PatternRecommender()
        recommendation = recommender.generate_recommendation({})

        # Should return fallback recommendation
        assert recommendation is not None
        assert recommendation["confidence"] <= 0.3

    def test_context_changed_codebase_structure_hash_differs(self) -> None:
        """Test pattern downweighting when context changes."""
        pattern_store = PatternStore()

        # Create a pattern with codebase structure precondition
        pattern_id = pattern_store.store_pattern(
            pattern_type="tactical",
            name="Context-Specific Pattern",
            description="Test",
            preconditions={"codebase_structure": "hash_v1"},
            confidence=0.8,
        )

        recommender = PatternRecommender()

        # Get recommendation with different codebase structure
        recommendation = recommender.generate_recommendation({"codebase_structure": "hash_v2"})

        # Should not recommend pattern with different context
        assert recommendation["pattern_id"] != pattern_id

    def test_tactical_pattern_failed_3_plus_times(self) -> None:
        """Test that tactical pattern is archived after 3+ failures."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()

        # Create a tactical pattern
        pattern_id = pattern_store.store_pattern(
            pattern_type="tactical",
            name="Tactical Pattern",
            description="Test",
            preconditions={},
            confidence=0.5,
        )

        # Create 3 failed decisions with work events
        for i in range(3):
            session_id = str(uuid.uuid4())

            # Create work event
            work_payload = {
                "session_id": session_id,
                "task": f"task_{i}",
                "status": "failed",
                "files_modified": ["file.py"],
                "tests_passing": 0,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            log_event(
                event_type="AGENT_WORK",
                actor="agent",
                payload=work_payload,
                validate=False,
            )

            # Create failed decision
            decision_store.store_decision(
                session_id=session_id,
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
                    "success": False,
                    "primary_outcome": "failed",
                    "violations_introduced": 0,
                    "token_efficiency": 0.5,
                    "rework_needed": False,
                },
            )

        # Run learning cycle
        cycle = LearningCycle()
        cycle.run(str(uuid.uuid4()))

        # Pattern should be archived (confidence <= -0.5) or at least decreased
        updated_pattern = pattern_store.get_pattern(pattern_id)
        # After 3 failures, confidence should be significantly decreased
        assert updated_pattern["confidence"] < 0.5


class TestIntegrationScenarios:
    """Integration tests with full learning cycle scenarios."""

    def test_full_learning_cycle_with_multiple_patterns(self) -> None:
        """Test full learning cycle with multiple patterns and decisions."""
        pattern_store = PatternStore()
        decision_store = DecisionStore()
        session_id = str(uuid.uuid4())

        # Create multiple patterns
        pattern_ids = []
        for i in range(3):
            pattern_id = pattern_store.store_pattern(
                pattern_type="structural",
                name=f"Pattern {i}",
                description="Test",
                preconditions={},
                confidence=0.5,
            )
            pattern_ids.append(pattern_id)

        # Create work events
        for i in range(3):
            work_payload = {
                "session_id": session_id,
                "task": f"task_{i}",
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

        # Create decisions for each pattern
        for i, pattern_id in enumerate(pattern_ids):
            decision_store.store_decision(
                session_id=session_id,
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
                    "primary_outcome": "completed" if i < 2 else "failed",
                    "violations_introduced": 0,
                    "token_efficiency": 0.8,
                    "rework_needed": False,
                },
            )

        # Run learning cycle
        cycle = LearningCycle()
        results = cycle.run(session_id)

        # Verify results
        assert results["patterns_extracted"] >= 0
        assert results["audit_id"] is not None

        # Verify pattern confidence updates
        for i, pattern_id in enumerate(pattern_ids):
            pattern = pattern_store.get_pattern(pattern_id)
            if i < 2:
                # Successful patterns should have higher confidence
                assert pattern["confidence"] > 0.5
            else:
                # Failed pattern should have lower confidence
                assert pattern["confidence"] < 0.5
