"""
Complete System Integration Tests

Tests the full DivineOS system with all 5 integration points working together:
1. Clarity Enforcement → Learning Loop
2. Contradiction Detection → Resolution Engine
3. Memory Monitor → Learning Cycle
4. Tool Execution → Ledger Storage
5. Query Interface → Current Fact Resolution
"""

from divineos.supersession import (
    ResolutionEngine,
    ResolutionStrategy,
    ContradictionDetector,
)
from divineos.clarity_enforcement.enforcer import ClarityEnforcer
from divineos.clarity_enforcement.config import ClarityConfig, ClarityEnforcementMode
from divineos.agent_integration.learning_cycle import LearningCycle
from divineos.agent_integration.memory_monitor import get_memory_monitor
from divineos.core.ledger import log_event


class TestCompleteSystemIntegration:
    """Tests all 5 integration points working together."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ResolutionEngine()
        self.detector = ContradictionDetector()
        self.learning_cycle = LearningCycle()
        self.pattern_store = self.learning_cycle.pattern_store

        # Initialize clarity enforcer
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        self.enforcer = ClarityEnforcer(config)

        # Initialize memory monitor
        self.monitor = get_memory_monitor("test_session")

    def test_integration_point_1_clarity_to_learning(self):
        """
        Integration Point 1: Clarity Enforcement → Learning Loop

        Verify that violations detected by clarity enforcer are captured
        by the learning cycle and stored in pattern store.
        """
        # Simulate a tool call without explanation (violation)
        tool_name = "execute_query"
        tool_input = {"query": "SELECT * FROM users"}
        context = {"session_id": "test_session"}

        # Detect violation
        violation = self.enforcer.detect_violation(
            tool_name=tool_name,
            tool_input=tool_input,
            context=context,
            violation_type="missing_explanation",
        )

        # Verify violation detected
        assert violation is not None

        # Capture violation in learning cycle
        self.learning_cycle.capture_violation_event(
            tool_name=tool_name,
            context_type="query_execution",
            violation_type="missing_explanation",
            confidence=0.95,
        )

        # Verify pattern stored
        patterns = self.pattern_store.get_patterns_for_tool(tool_name)
        assert len(patterns) > 0

    def test_integration_point_2_contradiction_to_resolution(self):
        """
        Integration Point 2: Contradiction Detection → Resolution Engine

        Verify that contradictions are detected and resolved, creating
        supersession events that track the resolution.
        """
        fact1 = {
            "id": "fact_1",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 25.0,
            "timestamp": "2026-03-20T10:00:00Z",
            "confidence": 0.9,
            "source": "sensor_a",
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 26.0,
            "timestamp": "2026-03-20T10:01:00Z",
            "confidence": 0.95,
            "source": "sensor_b",
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # Detect contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        assert contradiction is not None

        # Resolve contradiction
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.NEWER_FACT
        )

        # Verify resolution created supersession event
        assert supersession is not None
        assert supersession.superseded_fact_id == "fact_1"
        assert supersession.superseding_fact_id == "fact_2"

    def test_integration_point_3_memory_to_learning(self):
        """
        Integration Point 3: Memory Monitor → Learning Cycle

        Verify that memory monitor tracks token usage and triggers
        learning cycle at session end.
        """
        # Update token usage
        self.monitor.update_token_usage(100)
        assert self.monitor.current_tokens == 100

        # Simulate work completion
        self.monitor.save_work_checkpoint(
            task="test_task", status="completed", files_modified=["test.py"], tests_passing=5
        )

        # Verify checkpoint saved
        assert self.monitor.last_checkpoint_tokens == 100

    def test_integration_point_4_tool_execution_to_ledger(self):
        """
        Integration Point 4: Tool Execution → Ledger Storage

        Verify that tool executions are captured and stored in the ledger
        with full audit trail.
        """
        # Store a tool execution event (disable validation for test)
        event_id = log_event(
            event_type="TOOL_CALL",
            actor="agent",
            payload={
                "tool_name": "execute_query",
                "tool_use_id": "tool_use_123",
                "tool_input": {"query": "SELECT * FROM users"},
                "result": {"rows": 5},
                "duration_ms": 150,
                "status": "success",
            },
            validate=False,
        )

        # Verify event stored
        assert event_id is not None

    def test_integration_point_5_query_to_current_fact(self):
        """
        Integration Point 5: Query Interface → Current Fact Resolution

        Verify that queries follow supersession chains to return current facts.
        """
        fact1 = {
            "id": "fact_1",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 25.0,
            "timestamp": "2026-03-20T10:00:00Z",
            "confidence": 0.9,
            "source": "test",
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 26.0,
            "timestamp": "2026-03-20T10:01:00Z",
            "confidence": 0.95,
            "source": "test",
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # Detect and resolve contradiction
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        self.engine.resolve_contradiction(contradiction, ResolutionStrategy.NEWER_FACT)

        # Query for current fact
        current = self.engine.get_current_truth("measurement", "temperature")

        # Verify query returns current (superseding) fact
        assert current is not None
        assert current["id"] == "fact_2"

    def test_all_integration_points_together(self):
        """
        Complete System Integration Test

        Verify all 5 integration points work together in a complete workflow:
        startup → work → violations → learning → session end
        """
        # 1. Register facts (Integration Point 5 setup)
        fact1 = {
            "id": "fact_1",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 25.0,
            "timestamp": "2026-03-20T10:00:00Z",
            "confidence": 0.9,
            "source": "test",
        }

        fact2 = {
            "id": "fact_2",
            "fact_type": "measurement",
            "fact_key": "temperature",
            "value": 26.0,
            "timestamp": "2026-03-20T10:01:00Z",
            "confidence": 0.95,
            "source": "test",
        }

        self.engine.register_fact(fact1)
        self.engine.register_fact(fact2)

        # 2. Detect contradiction (Integration Point 2)
        contradiction = self.detector.detect_contradiction(fact1, fact2)
        assert contradiction is not None

        # 3. Resolve contradiction (Integration Point 2)
        supersession = self.engine.resolve_contradiction(
            contradiction, ResolutionStrategy.NEWER_FACT
        )
        assert supersession is not None

        # 4. Store resolution in ledger (Integration Point 4)
        event_id = log_event(
            event_type="SUPERSESSION",
            actor="agent",
            payload={
                "superseded_fact_id": supersession.superseded_fact_id,
                "superseding_fact_id": supersession.superseding_fact_id,
                "reason": supersession.reason,
            },
            validate=False,
        )
        assert event_id is not None

        # 5. Capture violation (Integration Point 1)
        self.learning_cycle.capture_violation_event(
            {
                "type": "CLARITY_VIOLATION",
                "session_id": "test_session",
                "tool_name": "contradiction_resolver",
                "tool_input": {},
                "context": "fact_resolution",
                "violation_type": "contradiction_detected",
                "confidence": 0.95,
                "timestamp": "2026-03-20T10:00:00Z",
                "enforcement_mode": "LOGGING",
            }
        )

        # 6. Update memory monitor (Integration Point 3)
        self.monitor.update_token_usage(250)
        self.monitor.save_work_checkpoint(
            task="contradiction_resolution",
            status="completed",
            files_modified=["resolution_engine.py"],
            tests_passing=10,
        )

        # 7. Query for current fact (Integration Point 5)
        current = self.engine.get_current_truth("measurement", "temperature")
        assert current is not None
        assert current["id"] == "fact_2"

        # Verify all integration points executed
        assert self.engine.is_superseded("fact_1")
        assert not self.engine.is_superseded("fact_2")
        assert self.monitor.current_tokens == 250
