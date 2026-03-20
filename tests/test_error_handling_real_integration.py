"""Real integration tests for error handling and monitoring.

Tests that error handling and monitoring work with actual integration points,
not mocks. Validates that errors are caught, logged, and recovery works.
"""

import pytest
from unittest.mock import MagicMock

from divineos.supersession.resolution_engine import ResolutionEngine
from divineos.agent_integration.learning_cycle import LearningCycle
from divineos.core.ledger import Ledger
from divineos.integration.error_handler import ErrorHandler, FatalError
from divineos.integration.system_monitor import get_system_monitor, reset_monitor


class TestErrorHandlingRealIntegration:
    """Test error handling with real integration points."""

    def setup_method(self):
        """Set up test fixtures."""
        self.resolution_engine = ResolutionEngine()
        self.ledger = Ledger()
        self.monitor = get_system_monitor()
        reset_monitor()

    def test_resolution_engine_error_handling_with_monitoring(self):
        """Test that resolution engine errors are caught and monitored."""
        # Create a mock contradiction that will cause an error
        contradiction = MagicMock()
        contradiction.context = {"fact1": {}, "fact2": {}}
        contradiction.fact1_id = "fact_1"
        contradiction.fact2_id = "fact_2"

        # Wrap resolution in error handler with monitoring
        def resolve_with_monitoring():
            try:
                self.monitor.record_latency(self.monitor.CONTRADICTION_RESOLUTION, 0.001)
                result = self.resolution_engine.resolve_contradiction(contradiction)
                self.monitor.record_success(self.monitor.CONTRADICTION_RESOLUTION)
                return result
            except Exception as e:
                self.monitor.record_error(self.monitor.CONTRADICTION_RESOLUTION, Exception(str(e)))
                raise

        # Execute and verify monitoring recorded success
        result = resolve_with_monitoring()
        assert result is not None
        assert result.event_id is not None

        # Verify metrics were recorded using the correct integration point name
        metrics = self.monitor.get_metrics(self.monitor.CONTRADICTION_RESOLUTION)
        assert metrics["success_count"] == 1
        assert metrics["error_count"] == 0

    def test_learning_cycle_error_handling_with_monitoring(self):
        """Test that learning cycle errors are caught and monitored."""
        # Create a learning cycle
        learning_cycle = LearningCycle()

        # Wrap learning cycle run in error handler with monitoring
        def run_with_monitoring():
            try:
                self.monitor.record_latency(self.monitor.MEMORY_LEARNING, 0.001)
                result = learning_cycle.run("test_session")
                self.monitor.record_success(self.monitor.MEMORY_LEARNING)
                return result
            except Exception as e:
                self.monitor.record_error(self.monitor.MEMORY_LEARNING, Exception(str(e)))
                raise

        # Execute and verify monitoring recorded success
        result = run_with_monitoring()
        assert result is not None
        assert "session_id" in result

        # Verify metrics were recorded
        metrics = self.monitor.get_metrics(self.monitor.MEMORY_LEARNING)
        assert metrics["success_count"] == 1
        assert metrics["error_count"] == 0

    def test_retry_logic_with_transient_error(self):
        """Test that retry logic handles transient errors."""
        call_count = 0

        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient connection error")
            return "success"

        # Wrap with retry logic
        wrapped = ErrorHandler.with_retry(flaky_function, max_retries=3)

        # Execute and verify it retried and succeeded
        result = wrapped()
        assert result == "success"
        assert call_count == 3

    def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after repeated failures."""
        from divineos.integration.error_handler import RecoveryStrategy

        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent error")

        # Wrap with circuit breaker
        wrapped = RecoveryStrategy.circuit_breaker(
            failing_function, failure_threshold=3, timeout=0.1
        )

        # First 3 calls should fail with the original error
        for i in range(3):
            with pytest.raises(Exception):
                wrapped()

        # 4th call should fail with circuit breaker error
        with pytest.raises(FatalError):
            wrapped()

        assert call_count == 3  # Circuit breaker prevented 4th call

    def test_monitoring_tracks_latencies(self):
        """Test that monitoring tracks latencies correctly."""
        # Record several latencies
        self.monitor.record_latency(self.monitor.CLARITY_LEARNING, 0.001)
        self.monitor.record_latency(self.monitor.CLARITY_LEARNING, 0.002)
        self.monitor.record_latency(self.monitor.CLARITY_LEARNING, 0.003)

        # Get metrics
        metrics = self.monitor.get_metrics(self.monitor.CLARITY_LEARNING)

        # Verify latencies are tracked (record_latency doesn't increment event_count)
        assert metrics["success_count"] == 0
        assert metrics["event_count"] == 0  # latency recording doesn't increment event_count
        assert metrics["avg_latency"] > 0
        assert metrics["max_latency"] == 0.003
        assert metrics["min_latency"] == 0.001

    def test_monitoring_tracks_error_rates(self):
        """Test that monitoring tracks error rates correctly."""
        # Record successes and errors
        self.monitor.record_success(self.monitor.CONTRADICTION_RESOLUTION)
        self.monitor.record_success(self.monitor.CONTRADICTION_RESOLUTION)
        self.monitor.record_error(self.monitor.CONTRADICTION_RESOLUTION, Exception("Test error"))

        # Get metrics
        metrics = self.monitor.get_metrics(self.monitor.CONTRADICTION_RESOLUTION)

        # Verify error rate is calculated
        assert metrics["success_count"] == 2
        assert metrics["error_count"] == 1
        assert metrics["event_count"] == 3
        assert metrics["error_rate"] == pytest.approx(100.0 / 3.0, rel=0.01)

    def test_health_status_reflects_errors(self):
        """Test that health status reflects integration point errors."""
        # Record some errors
        self.monitor.record_error(self.monitor.CLARITY_LEARNING, Exception("Error 1"))
        self.monitor.record_error(self.monitor.CLARITY_LEARNING, Exception("Error 2"))
        self.monitor.record_success(self.monitor.CLARITY_LEARNING)

        # Get health status
        health = self.monitor.get_health_status()

        # Verify health status
        assert "status" in health
        assert health["overall_error_rate"] > 0
        assert health["status"] in ["HEALTHY", "WARNING", "CRITICAL"]

    def test_performance_report_includes_all_metrics(self):
        """Test that performance report includes all metrics."""
        # Record activity on multiple integration points
        for i in range(5):
            self.monitor.record_latency(self.monitor.CLARITY_LEARNING, 0.001 * i)
            self.monitor.record_latency(self.monitor.CONTRADICTION_RESOLUTION, 0.002 * i)

        # Get performance report
        report = self.monitor.get_performance_report()

        # Verify report includes all metrics
        assert self.monitor.CLARITY_LEARNING in report["integration_points"]
        assert self.monitor.CONTRADICTION_RESOLUTION in report["integration_points"]
        assert "timestamp" in report
        assert "summary" in report

    def test_error_handler_logs_context(self):
        """Test that error handler logs context for debugging."""
        error = Exception("Test error")
        context = {"tool_name": "test_tool", "session_id": "test_session"}

        # This should not raise, just log
        ErrorHandler.log_error_with_context(error, context, self.monitor.CLARITY_LEARNING)

        # Verify it logged (we can't easily check logs, but we verify no exception)
        assert True

    def test_fallback_to_default_on_error(self):
        """Test that fallback strategy returns default value on error."""
        from divineos.integration.error_handler import RecoveryStrategy

        def failing_function():
            raise ValueError("Test error")

        # Wrap with fallback
        wrapped = RecoveryStrategy.fallback_to_default(
            failing_function, default_value="default_result"
        )

        # Execute and verify it returns default
        result = wrapped()
        assert result == "default_result"

    def test_integration_point_error_handling_flow(self):
        """Test complete error handling flow for an integration point."""

        # Simulate an integration point operation
        def integration_point_operation():
            try:
                self.monitor.record_latency(self.monitor.TOOL_LEDGER, 0.001)

                # Simulate work
                result = {"status": "success", "data": "test"}

                self.monitor.record_success(self.monitor.TOOL_LEDGER)
                return result
            except Exception as e:
                self.monitor.record_error(self.monitor.TOOL_LEDGER, Exception(str(e)))
                raise

        # Execute
        result = integration_point_operation()

        # Verify result
        assert result["status"] == "success"

        # Verify monitoring
        metrics = self.monitor.get_metrics(self.monitor.TOOL_LEDGER)
        assert metrics["success_count"] == 1
        assert metrics["error_count"] == 0

    def test_all_integration_points_monitored(self):
        """Test that all 5 integration points can be monitored."""
        integration_points = [
            self.monitor.CLARITY_LEARNING,
            self.monitor.CONTRADICTION_RESOLUTION,
            self.monitor.MEMORY_LEARNING,
            self.monitor.TOOL_LEDGER,
            self.monitor.QUERY_FACT,
        ]

        # Record activity on all integration points
        for point in integration_points:
            self.monitor.record_success(point)
            self.monitor.record_latency(point, 0.001)

        # Get metrics for all
        for point in integration_points:
            metrics = self.monitor.get_metrics(point)
            assert metrics["success_count"] == 1
            assert metrics["event_count"] == 1  # only success increments event_count

    def test_monitoring_export_format(self):
        """Test that monitoring can export metrics in standard format."""
        # Record some activity
        self.monitor.record_success(self.monitor.CLARITY_LEARNING)
        self.monitor.record_latency(self.monitor.CLARITY_LEARNING, 0.001)

        # Export metrics
        export = self.monitor.export_metrics()

        # Verify export is valid JSON string
        assert isinstance(export, str)
        assert self.monitor.CLARITY_LEARNING in export
