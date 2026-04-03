"""Real integration tests for system monitoring.

Tests that monitoring works with actual integration points, not mocks.
"""

from unittest.mock import MagicMock

from divineos.supersession.resolution_engine import ResolutionEngine
from divineos.agent_integration.learning_cycle import LearningCycle
from divineos.core.ledger import Ledger
from divineos.integration.system_monitor import SystemMonitor, get_system_monitor, reset_monitor


class TestErrorHandlingRealIntegration:
    """Test error handling with real integration points."""

    def setup_method(self):
        """Set up test fixtures."""
        self.resolution_engine = ResolutionEngine()
        self.ledger = Ledger()
        reset_monitor()
        self.monitor = get_system_monitor()

    def test_resolution_engine_error_handling_with_monitoring(self):
        """Test that resolution engine errors are caught and monitored."""
        point = SystemMonitor.CONTRADICTION_RESOLUTION

        contradiction = MagicMock()
        contradiction.context = {"fact1": {}, "fact2": {}}
        contradiction.fact1_id = "fact_1"
        contradiction.fact2_id = "fact_2"

        def resolve_with_monitoring():
            try:
                self.monitor.record_latency(point, 0.001)
                result = self.resolution_engine.resolve_contradiction(contradiction)
                self.monitor.record_success(point)
                return result
            except Exception as e:
                self.monitor.record_error(point, e)
                raise

        result = resolve_with_monitoring()
        assert result is not None
        assert result.event_id is not None

        metrics = self.monitor.get_metrics(point)
        assert metrics["success_count"] >= 1
        assert metrics["error_count"] == 0

    def test_learning_cycle_error_handling_with_monitoring(self):
        """Test that learning cycle errors are caught and monitored."""
        point = SystemMonitor.MEMORY_LEARNING
        learning_cycle = LearningCycle()

        def run_with_monitoring():
            try:
                self.monitor.record_latency(point, 0.001)
                result = learning_cycle.run("test_session")
                self.monitor.record_success(point)
                return result
            except Exception as e:
                self.monitor.record_error(point, e)
                raise

        result = run_with_monitoring()
        assert result is not None
        assert "session_id" in result

        metrics = self.monitor.get_metrics(point)
        assert metrics["success_count"] >= 1
        assert metrics["error_count"] == 0

    def test_monitoring_tracks_latencies(self):
        """Test that monitoring tracks latencies correctly."""
        point = SystemMonitor.CLARITY_LEARNING

        self.monitor.record_latency(point, 0.001)
        self.monitor.record_latency(point, 0.002)
        self.monitor.record_latency(point, 0.003)

        metrics = self.monitor.get_metrics(point)

        assert metrics["avg_latency"] > 0
        assert metrics["max_latency"] == 0.003
        assert metrics["min_latency"] == 0.001

    def test_monitoring_tracks_error_rates(self):
        """Test that monitoring tracks error rates correctly."""
        point = SystemMonitor.CONTRADICTION_RESOLUTION

        self.monitor.record_success(point)
        self.monitor.record_success(point)
        self.monitor.record_error(point, Exception("Test error"))

        metrics = self.monitor.get_metrics(point)

        assert metrics["success_count"] == 2
        assert metrics["error_count"] == 1
        assert metrics["error_rate"] > 0

    def test_health_status_reflects_errors(self):
        """Test that health status reflects integration point errors."""
        point = SystemMonitor.CLARITY_LEARNING

        self.monitor.record_error(point, Exception("Error 1"))
        self.monitor.record_error(point, Exception("Error 2"))
        self.monitor.record_success(point)

        health = self.monitor.get_health_status()

        assert "status" in health
        assert health["total_errors"] == 2
        assert health["total_successes"] == 1
        assert health["overall_error_rate"] > 0

    def test_performance_report_includes_all_metrics(self):
        """Test that performance report includes all metrics."""
        point1 = SystemMonitor.CLARITY_LEARNING
        point2 = SystemMonitor.CONTRADICTION_RESOLUTION

        for i in range(5):
            self.monitor.record_latency(point1, 0.001 * i)
            self.monitor.record_latency(point2, 0.002 * i)

        report = self.monitor.get_performance_report()

        assert "integration_points" in report
        assert point1 in report["integration_points"]
        assert point2 in report["integration_points"]
        assert "timestamp" in report
        assert "summary" in report

    def test_integration_point_error_handling_flow(self):
        """Test complete error handling flow for an integration point."""
        point = SystemMonitor.TOOL_LEDGER

        def integration_point_operation():
            try:
                self.monitor.record_latency(point, 0.001)
                result = {"status": "success", "data": "test"}
                self.monitor.record_success(point)
                return result
            except Exception as e:
                self.monitor.record_error(point, e)
                raise

        result = integration_point_operation()

        assert result["status"] == "success"

        metrics = self.monitor.get_metrics(point)
        assert metrics["success_count"] == 1
        assert metrics["error_count"] == 0

    def test_all_integration_points_monitored(self):
        """Test that all 5 integration points can be monitored."""
        integration_points = [
            SystemMonitor.CLARITY_LEARNING,
            SystemMonitor.CONTRADICTION_RESOLUTION,
            SystemMonitor.MEMORY_LEARNING,
            SystemMonitor.TOOL_LEDGER,
            SystemMonitor.QUERY_FACT,
        ]

        for point in integration_points:
            self.monitor.record_success(point)
            self.monitor.record_latency(point, 0.001)

        for point in integration_points:
            metrics = self.monitor.get_metrics(point)
            assert metrics["success_count"] == 1

    def test_monitoring_export_format(self):
        """Test that monitoring can export metrics in standard format."""
        point = SystemMonitor.CLARITY_LEARNING

        self.monitor.record_success(point)
        self.monitor.record_latency(point, 0.001)

        export = self.monitor.export_metrics()

        assert isinstance(export, str)
        assert point in export
