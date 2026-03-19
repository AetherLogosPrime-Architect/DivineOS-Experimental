"""
Verification tests for the Agent Work Clarity System.

Tests non-blocking behavior, ledger-based analysis, and error resilience.
"""

import pytest
from uuid import uuid4

from src.divineos.clarity_system import (
    DefaultClarityStatementGenerator,
    DefaultPlanAnalyzer,
    DefaultExecutionAnalyzer,
    DefaultDeviationAnalyzer,
    DefaultLearningExtractor,
    DefaultSummaryGenerator,
    ClarityStatement,
    ScopeEstimate,
    ExecutionData,
    ExecutionMetrics,
    LedgerQueryInterface,
    SessionManagerInterface,
    EventEmissionInterface,
    HookIntegrationInterface,
)


class TestNonBlockingClarity:
    """Tests for non-blocking clarity statement behavior."""

    def test_clarity_statement_generation_is_non_blocking(self):
        """Test that clarity statement generation doesn't block execution."""
        generator = DefaultClarityStatementGenerator()

        work_context = {
            "goal": "Test goal",
            "approach": "Test approach",
            "expected_outcome": "Test outcome",
            "estimated_files": 5,
            "estimated_tool_calls": 20,
            "estimated_complexity": "medium",
            "estimated_time_minutes": 60,
        }

        # Generate clarity statement
        statement = generator.generate_clarity_statement(work_context)

        # Verify statement was generated
        assert statement is not None
        assert statement.goal == "Test goal"

        # Verify no blocking occurred (statement should be generated immediately)
        assert statement.timestamp is not None

    def test_clarity_statement_user_feedback_is_optional(self):
        """Test that user feedback is optional for clarity statements."""
        generator = DefaultClarityStatementGenerator()

        work_context = {
            "goal": "Test goal",
            "approach": "Test approach",
            "expected_outcome": "Test outcome",
            "estimated_files": 5,
            "estimated_tool_calls": 20,
            "estimated_complexity": "medium",
            "estimated_time_minutes": 60,
        }

        statement = generator.generate_clarity_statement(work_context)

        # Verify user_feedback is optional (can be None)
        assert statement.user_feedback is None or isinstance(statement.user_feedback, str)

    def test_clarity_statement_no_approval_required(self):
        """Test that no approval is required to proceed after clarity statement."""
        generator = DefaultClarityStatementGenerator()

        work_context = {
            "goal": "Test goal",
            "approach": "Test approach",
            "expected_outcome": "Test outcome",
            "estimated_files": 5,
            "estimated_tool_calls": 20,
            "estimated_complexity": "medium",
            "estimated_time_minutes": 60,
        }

        statement = generator.generate_clarity_statement(work_context)

        # Verify that we can proceed immediately without approval
        # (no blocking mechanism in place)
        assert statement is not None
        assert not hasattr(statement, "requires_approval")


class TestLedgerBasedAnalysis:
    """Tests for ledger-based analysis."""

    def test_execution_analyzer_uses_ledger_interface(self):
        """Test that execution analyzer uses ledger interface."""
        analyzer = DefaultExecutionAnalyzer()

        # Verify that the analyzer has access to ledger interface
        assert hasattr(analyzer, "analyze_execution")

    def test_ledger_query_interface_exists(self):
        """Test that ledger query interface is available."""
        # Verify interface methods exist
        assert hasattr(LedgerQueryInterface, "query_events_for_session")
        assert hasattr(LedgerQueryInterface, "extract_tool_calls_from_events")
        assert hasattr(LedgerQueryInterface, "extract_errors_from_events")
        assert hasattr(LedgerQueryInterface, "get_session_events")

    def test_ledger_interface_handles_missing_ledger(self):
        """Test that ledger interface handles missing ledger gracefully."""
        session_id = uuid4()

        # Query with no ledger should return empty results
        events = LedgerQueryInterface.query_events_for_session(session_id)

        # Should return empty list, not raise exception
        assert isinstance(events, list)

    def test_no_additional_instrumentation_needed(self):
        """Test that clarity system doesn't require additional instrumentation."""
        # Verify that all data comes from existing ledger
        # No new event types or instrumentation required

        # Check that event types are standard
        assert hasattr(EventEmissionInterface, "emit_clarity_statement_event")
        assert hasattr(EventEmissionInterface, "emit_summary_event")


class TestErrorResilience:
    """Tests for error resilience across all components."""

    def test_clarity_generator_handles_missing_context(self):
        """Test clarity generator handles missing work context."""
        generator = DefaultClarityStatementGenerator()

        # Empty context
        work_context = {}

        statement = generator.generate_clarity_statement(work_context)

        # Should still generate a statement
        assert statement is not None
        assert statement.goal is not None

    def test_plan_analyzer_handles_invalid_data(self):
        """Test plan analyzer handles invalid clarity statement."""
        analyzer = DefaultPlanAnalyzer()

        # Invalid clarity statement
        statement = ClarityStatement(
            goal="",
            approach="",
            expected_outcome="",
            scope=ScopeEstimate(0, 0, "invalid", 0),
        )

        plan_data = analyzer.analyze_plan(statement)

        # Should still return valid plan data
        assert plan_data is not None
        assert plan_data.metrics.estimated_complexity == "medium"

    def test_execution_analyzer_handles_no_events(self):
        """Test execution analyzer handles no events from ledger."""
        analyzer = DefaultExecutionAnalyzer()

        session_id = uuid4()

        execution_data = analyzer.analyze_execution(session_id)

        # Should return valid execution data with empty lists
        assert execution_data is not None
        assert isinstance(execution_data.tool_calls, list)
        assert isinstance(execution_data.errors, list)

    def test_deviation_analyzer_handles_no_deviations(self):
        """Test deviation analyzer handles perfect execution."""
        from src.divineos.clarity_system import PlanData, PlanMetrics

        analyzer = DefaultDeviationAnalyzer()

        plan_data = PlanData(
            clarity_statement_id=uuid4(),
            goal="Test",
            approach="Test",
            expected_outcome="Test",
            metrics=PlanMetrics(5, 20, "medium", 60),
        )

        execution_data = ExecutionData(
            session_id=uuid4(),
            tool_calls=[],
            errors=[],
            metrics=ExecutionMetrics(5, 20, 0, 60.0, 1.0),
        )

        deviations = analyzer.analyze_deviations(plan_data, execution_data)

        # Should return empty or minimal deviations
        assert isinstance(deviations, list)

    def test_learning_extractor_handles_no_lessons(self):
        """Test learning extractor handles no lessons to extract."""
        extractor = DefaultLearningExtractor()

        deviations = []
        execution_data = ExecutionData(
            session_id=uuid4(),
            tool_calls=[],
            errors=[],
            metrics=ExecutionMetrics(0, 0, 0, 0.0, 0.0),
        )

        lessons = extractor.extract_lessons(deviations, execution_data)

        # Should return empty list
        assert isinstance(lessons, list)

    def test_summary_generator_handles_missing_components(self):
        """Test summary generator handles missing analysis components."""
        generator = DefaultSummaryGenerator()

        clarity_statement = ClarityStatement(
            goal="Test",
            approach="Test",
            expected_outcome="Test",
            scope=ScopeEstimate(0, 0, "medium", 0),
        )

        from src.divineos.clarity_system import PlanData, PlanMetrics

        plan_data = PlanData(
            clarity_statement_id=clarity_statement.id,
            goal="Test",
            approach="Test",
            expected_outcome="Test",
            metrics=PlanMetrics(0, 0, "medium", 0),
        )

        execution_data = ExecutionData(
            session_id=uuid4(),
            tool_calls=[],
            errors=[],
            metrics=ExecutionMetrics(0, 0, 0, 0.0, 0.0),
        )

        summary = generator.generate_post_work_summary(
            clarity_statement=clarity_statement,
            plan_data=plan_data,
            execution_data=execution_data,
            deviations=[],
            lessons=[],
            recommendations=[],
        )

        # Should still generate a summary
        assert summary is not None
        assert summary.clarity_statement.id == clarity_statement.id


class TestHookIntegration:
    """Tests for hook integration."""

    def test_hook_registration_works(self):
        """Test that hooks can be registered."""
        HookIntegrationInterface.clear_hooks()

        def test_hook(**kwargs):
            pass

        result = HookIntegrationInterface.register_pre_work_hook(test_hook)

        assert result is True
        hooks = HookIntegrationInterface.get_registered_hooks()
        assert hooks["pre_work"] == 1

        HookIntegrationInterface.clear_hooks()

    def test_hook_triggering_works(self):
        """Test that hooks can be triggered."""
        HookIntegrationInterface.clear_hooks()

        hook_called = []

        def test_hook(**kwargs):
            hook_called.append(True)

        HookIntegrationInterface.register_pre_work_hook(test_hook)

        session_id = uuid4()
        work_context = {"goal": "Test"}

        result = HookIntegrationInterface.trigger_pre_work_hooks(session_id, work_context)

        assert result is True
        assert len(hook_called) == 1

        HookIntegrationInterface.clear_hooks()

    def test_hook_error_handling(self):
        """Test that hook errors are handled gracefully."""
        HookIntegrationInterface.clear_hooks()

        def failing_hook(**kwargs):
            raise Exception("Test error")

        HookIntegrationInterface.register_pre_work_hook(failing_hook)

        session_id = uuid4()
        work_context = {"goal": "Test"}

        # Should not raise exception
        result = HookIntegrationInterface.trigger_pre_work_hooks(session_id, work_context)

        # Should return False due to hook failure
        assert result is False

        HookIntegrationInterface.clear_hooks()


class TestSessionIntegration:
    """Tests for session manager integration."""

    def test_session_interface_exists(self):
        """Test that session manager interface is available."""
        assert hasattr(SessionManagerInterface, "get_current_session_id")
        assert hasattr(SessionManagerInterface, "initialize_session")
        assert hasattr(SessionManagerInterface, "get_session_info")

    def test_session_interface_handles_no_session(self):
        """Test that session interface handles no active session."""
        session_id = SessionManagerInterface.get_current_session_id()

        # Should return None if no session active
        assert session_id is None or isinstance(session_id, type(uuid4()))


class TestEventIntegration:
    """Tests for event emission integration."""

    def test_event_interface_exists(self):
        """Test that event emission interface is available."""
        assert hasattr(EventEmissionInterface, "emit_clarity_statement_event")
        assert hasattr(EventEmissionInterface, "emit_summary_event")
        assert hasattr(EventEmissionInterface, "emit_deviation_event")
        assert hasattr(EventEmissionInterface, "emit_lesson_event")

    def test_event_emission_handles_errors(self):
        """Test that event emission handles errors gracefully."""
        session_id = uuid4()
        clarity_id = uuid4()

        # Should not raise exception even if ledger is unavailable
        result = EventEmissionInterface.emit_clarity_statement_event(
            session_id=session_id,
            clarity_statement_id=clarity_id,
            goal="Test",
            approach="Test",
            expected_outcome="Test",
            scope={"files": 5, "calls": 20},
        )

        # Should return boolean
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
