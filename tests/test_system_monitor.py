"""Tests for system monitoring and observability."""

from divineos.integration.system_monitor import (
    SystemMonitor,
    IntegrationPointMetrics,
    get_system_monitor,
    reset_monitor,
)


class TestIntegrationPointMetrics:
    """Tests for IntegrationPointMetrics."""

    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        metrics = IntegrationPointMetrics(name="test")
        metrics.error_count = 10
        metrics.success_count = 90

        assert metrics.error_rate == 10.0

    def test_error_rate_no_events(self):
        """Test error rate with no events."""
        metrics = IntegrationPointMetrics(name="test")

        assert metrics.error_rate == 0.0

    def test_avg_latency_calculation(self):
        """Test average latency calculation."""
        metrics = IntegrationPointMetrics(name="test")
        metrics.latencies = [100.0, 150.0, 200.0]

        assert metrics.avg_latency == 150.0

    def test_max_latency(self):
        """Test maximum latency."""
        metrics = IntegrationPointMetrics(name="test")
        metrics.latencies = [100.0, 150.0, 200.0]

        assert metrics.max_latency == 200.0

    def test_min_latency(self):
        """Test minimum latency."""
        metrics = IntegrationPointMetrics(name="test")
        metrics.latencies = [100.0, 150.0, 200.0]

        assert metrics.min_latency == 100.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = IntegrationPointMetrics(name="test")
        metrics.latencies = [100.0, 150.0]
        metrics.error_count = 5
        metrics.success_count = 95

        result = metrics.to_dict()

        assert result["name"] == "test"
        assert result["error_rate"] == 5.0
        assert result["avg_latency"] == 125.0
        assert result["error_count"] == 5
        assert result["success_count"] == 95


class TestSystemMonitor:
    """Tests for SystemMonitor."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_monitor()
        self.monitor = SystemMonitor()

    def test_initialization(self):
        """Test monitor initialization."""
        assert len(self.monitor.metrics) == 5
        assert self.monitor.CLARITY_LEARNING in self.monitor.metrics
        assert self.monitor.CONTRADICTION_RESOLUTION in self.monitor.metrics
        assert self.monitor.MEMORY_LEARNING in self.monitor.metrics
        assert self.monitor.TOOL_LEDGER in self.monitor.metrics
        assert self.monitor.QUERY_FACT in self.monitor.metrics

    def test_record_latency(self):
        """Test recording latency."""
        self.monitor.record_latency(self.monitor.CLARITY_LEARNING, 50.0)

        metrics = self.monitor.metrics[self.monitor.CLARITY_LEARNING]
        assert len(metrics.latencies) == 1
        assert metrics.latencies[0] == 50.0

    def test_record_success(self):
        """Test recording success."""
        self.monitor.record_success(self.monitor.CLARITY_LEARNING)

        metrics = self.monitor.metrics[self.monitor.CLARITY_LEARNING]
        assert metrics.success_count == 1
        assert metrics.event_count == 1

    def test_record_error(self):
        """Test recording error."""
        error = Exception("test error")
        self.monitor.record_error(self.monitor.CLARITY_LEARNING, error)

        metrics = self.monitor.metrics[self.monitor.CLARITY_LEARNING]
        assert metrics.error_count == 1
        assert metrics.event_count == 1
        assert "test error" in metrics.last_error

    def test_get_metrics_single_point(self):
        """Test getting metrics for single integration point."""
        self.monitor.record_latency(self.monitor.CLARITY_LEARNING, 75.0)
        self.monitor.record_success(self.monitor.CLARITY_LEARNING)

        metrics = self.monitor.get_metrics(self.monitor.CLARITY_LEARNING)

        assert metrics["name"] == self.monitor.CLARITY_LEARNING
        assert metrics["avg_latency"] == 75.0
        assert metrics["success_count"] == 1

    def test_get_metrics_all_points(self):
        """Test getting metrics for all integration points."""
        self.monitor.record_success(self.monitor.CLARITY_LEARNING)
        self.monitor.record_success(self.monitor.CONTRADICTION_RESOLUTION)

        metrics = self.monitor.get_metrics()

        assert len(metrics) == 5
        assert self.monitor.CLARITY_LEARNING in metrics
        assert self.monitor.CONTRADICTION_RESOLUTION in metrics

    def test_get_health_status_healthy(self):
        """Test health status when healthy."""
        for _ in range(100):
            self.monitor.record_success(self.monitor.CLARITY_LEARNING)

        health = self.monitor.get_health_status()

        assert health["status"] == "HEALTHY"
        assert health["overall_error_rate"] == 0.0
        assert health["total_events"] >= 100

    def test_get_health_status_warning(self):
        """Test health status when in warning state."""
        for _ in range(95):
            self.monitor.record_success(self.monitor.CLARITY_LEARNING)
        for _ in range(6):
            self.monitor.record_error(self.monitor.CLARITY_LEARNING, Exception("error"))

        health = self.monitor.get_health_status()

        assert health["status"] == "WARNING"
        assert health["overall_error_rate"] > 5.0

    def test_get_health_status_critical(self):
        """Test health status when critical."""
        for _ in range(85):
            self.monitor.record_success(self.monitor.CLARITY_LEARNING)
        for _ in range(15):
            self.monitor.record_error(self.monitor.CLARITY_LEARNING, Exception("error"))

        health = self.monitor.get_health_status()

        assert health["status"] == "CRITICAL"
        assert health["overall_error_rate"] > 10.0

    def test_get_performance_report(self):
        """Test performance report generation."""
        self.monitor.record_latency(self.monitor.CLARITY_LEARNING, 50.0)
        self.monitor.record_latency(self.monitor.CLARITY_LEARNING, 100.0)
        self.monitor.record_success(self.monitor.CLARITY_LEARNING)

        report = self.monitor.get_performance_report()

        assert "timestamp" in report
        assert "integration_points" in report
        assert "summary" in report
        assert report["summary"]["total_latency_samples"] == 2
        assert report["summary"]["avg_latency_all"] == 75.0

    def test_export_metrics_prometheus_format(self):
        """Test exporting metrics in Prometheus format."""
        self.monitor.record_latency(self.monitor.CLARITY_LEARNING, 75.0)
        self.monitor.record_success(self.monitor.CLARITY_LEARNING)
        self.monitor.record_error(self.monitor.CLARITY_LEARNING, Exception("error"))

        metrics_text = self.monitor.export_metrics()

        assert "divineos_integration_latency" in metrics_text
        assert "divineos_integration_errors" in metrics_text
        assert "divineos_integration_successes" in metrics_text
        assert "clarity_enforcement_to_learning" in metrics_text

    def test_get_system_monitor_singleton(self):
        """Test that get_system_monitor returns singleton."""
        reset_monitor()
        monitor1 = get_system_monitor()
        monitor2 = get_system_monitor()

        assert monitor1 is monitor2

    def test_unknown_integration_point(self):
        """Test handling of unknown integration point."""
        self.monitor.record_latency("unknown_point", 100.0)

        metrics = self.monitor.get_metrics("unknown_point")
        assert metrics == {}
