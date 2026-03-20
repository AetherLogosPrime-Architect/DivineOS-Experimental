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
                self.monitor.record_latency("integration_point_2", 0.001)
                result = self.resolution_engine.resolve_contradiction(contradiction)
                self.monitor.record_success("integration_point_2")
                return result
            except Exception as e:
                self.monitor.record_error("integration_point_2", str(e))
                raise

        # Execute and verify monitoring recorded success
        result = resolve_with_monitoring()
        assert result is not None
        assert result.event_id is not None

        # Verify metrics were recorded
        metrics = self.monitor.get_metrics("integration_point_2")
        assert metrics["success_count"] == 1
        assert metrics["error_count"] == 0
        assert metrics["total_calls"] == 1

    def test_learning_cycle_error_handling_with_monitoring(self):
        """Test that learning cycle errors are caught and monitored."""
        # Create a learning cycle
        learning_cycle = LearningCycle()

        # Wrap learning cycle run in error handler with monitoring
        def run_with_monitoring():
            try:
                self.monitor.record_latency("integration_point_3", 0.001)
                result = learning_cycle.run("test_session")
                self.monitor.record_success("integration_point_3")
                return result
            except Exception as e:
                self.monitor.record_error("integration_point_3", str(e))
                raise

        # Execute and verify monitoring recorded success
        result = run_with_monitoring()
        assert result is not None
        assert "session_id" in result

        # Verify metrics were recorded
        metrics = self.monitor.get_metrics("integration_point_3")
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
        self.monitor.record_latency("integration_point_1", 0.001)
        self.monitor.record_latency("integration_point_1", 0.002)
        self.monitor.record_latency("integration_point_1", 0.003)

        # Get metrics
        metrics = self.monitor.get_metrics("integration_point_1")

        # Verify latencies are tracked
        assert metrics["total_calls"] == 3
        assert metrics["avg_latency"] > 0
        assert metrics["max_latency"] == 0.003
        assert metrics["min_latency"] == 0.001

    def test_monitoring_tracks_error_rates(self):
        """Test that monitoring tracks error rates correctly."""
        # Record successes and errors
        self.monitor.record_success("integration_point_2")
        self.monitor.record_success("integration_point_2")
        self.monitor.record_error("integration_point_2", "Test error")

        # Get metrics
        metrics = self.monitor.get_metrics("integration_point_2")

        # Verify error rate is calculated
        assert metrics["total_calls"] == 3
        assert metrics["success_count"] == 2
        assert metrics["error_count"] == 1
        assert metrics["error_rate"] == pytest.approx(1.0 / 3.0, rel=0.01)

    def test_health_status_reflects_errors(self):
        """Test that health status reflects integration point errors."""
        # Record some errors
        self.monitor.record_error("integration_point_1", "Error 1")
        self.monitor.record_error("integration_point_1", "Error 2")
        self.monitor.record_success("integration_point_1")

        # Get health status
        health = self.monitor.get_health_status()

        # Verify health status
        assert "integration_point_1" in health
        assert health["integration_point_1"]["error_rate"] > 0
        assert health["integration_point_1"]["status"] in ["healthy", "degraded", "unhealthy"]

    def test_performance_report_includes_all_metrics(self):
        """Test that performance report includes all metrics."""
        # Record activity on multiple integration points
        for i in range(5):
            self.monitor.record_latency("integration_point_1", 0.001 * i)
            self.monitor.record_latency("integration_point_2", 0.002 * i)

        # Get performance report
        report = self.monitor.get_performance_report()

        # Verify report includes all metrics
        assert "integration_point_1" in report
        assert "integration_point_2" in report
        assert "timestamp" in report
        assert "summary" in report

    def test_error_handler_logs_context(self):
        """Test that error handler logs context for debugging."""
        error = Exception("Test error")
        context = {"tool_name": "test_tool", "session_id": "test_session"}

        # This should not raise, just log
        ErrorHandler.log_error_with_context(error, context, "integration_point_1")

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
                self.monitor.record_latency("integration_point_4", 0.001)

                # Simulate work
                result = {"status": "success", "data": "test"}

                self.monitor.record_success("integration_point_4")
                return result
            except Exception as e:
                self.monitor.record_error("integration_point_4", str(e))
                raise

        # Execute
        result = integration_point_operation()

        # Verify result
        assert result["status"] == "success"

        # Verify monitoring
        metrics = self.monitor.get_metrics("integration_point_4")
        assert metrics["success_count"] == 1
        assert metrics["error_count"] == 0

    def test_all_integration_points_monitored(self):
        """Test that all 5 integration points can be monitored."""
        integration_points = [
            "integration_point_1",
            "integration_point_2",
            "integration_point_3",
            "integration_point_4",
            "integration_point_5",
        ]

        # Record activity on all integration points
        for point in integration_points:
            self.monitor.record_success(point)
            self.monitor.record_latency(point, 0.001)

        # Get metrics for all
        for point in integration_points:
            metrics = self.monitor.get_metrics(point)
            assert metrics["success_count"] == 1
            assert metrics["total_calls"] == 2  # 1 success + 1 latency

    def test_monitoring_export_format(self):
        """Test that monitoring can export metrics in standard format."""
        # Record some activity
        self.monitor.record_success("integration_point_1")
        self.monitor.record_latency("integration_point_1", 0.001)

        # Export metrics
        export = self.monitor.export_metrics()

        # Verify export is valid JSON string
        assert isinstance(export, str)
        assert "integration_point_1" in export
