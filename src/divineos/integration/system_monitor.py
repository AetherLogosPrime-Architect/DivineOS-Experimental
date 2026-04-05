"""System monitoring and observability for DivineOS integration points.

Tracks metrics for each integration point including latencies, error rates,
and event counts to enable performance analysis and debugging.
"""

import time
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from loguru import logger


@dataclass
class MetricPoint:
    """A single metric measurement."""

    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class IntegrationPointMetrics:
    """Metrics for a single integration point."""

    name: str
    latencies: list[float] = field(default_factory=list)
    error_count: int = 0
    success_count: int = 0
    event_count: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        total = self.error_count + self.success_count
        if total == 0:
            return 0.0
        return (self.error_count / total) * 100

    @property
    def avg_latency(self) -> float:
        """Calculate average latency."""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def max_latency(self) -> float:
        """Get maximum latency."""
        return max(self.latencies) if self.latencies else 0.0

    @property
    def min_latency(self) -> float:
        """Get minimum latency."""
        return min(self.latencies) if self.latencies else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "name": self.name,
            "error_rate": self.error_rate,
            "avg_latency": self.avg_latency,
            "max_latency": self.max_latency,
            "min_latency": self.min_latency,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "event_count": self.event_count,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time,
        }


class SystemMonitor:
    """Monitors all integration points and collects metrics."""

    # Integration point names
    CLARITY_LEARNING = "clarity_enforcement_to_learning"
    CONTRADICTION_RESOLUTION = "contradiction_to_resolution"
    MEMORY_LEARNING = "memory_to_learning"
    TOOL_LEDGER = "tool_to_ledger"
    QUERY_FACT = "query_to_fact"

    # Performance targets (in milliseconds)
    LATENCY_TARGETS = {
        CLARITY_LEARNING: 100,
        CONTRADICTION_RESOLUTION: 150,
        MEMORY_LEARNING: 50,
        TOOL_LEDGER: 200,
        QUERY_FACT: 75,
    }

    def __init__(self):
        """Initialize system monitor."""
        self.metrics: Dict[str, IntegrationPointMetrics] = {}
        self.start_time = time.time()
        self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """Initialize metrics for all integration points."""
        for point_name in [
            self.CLARITY_LEARNING,
            self.CONTRADICTION_RESOLUTION,
            self.MEMORY_LEARNING,
            self.TOOL_LEDGER,
            self.QUERY_FACT,
        ]:
            self.metrics[point_name] = IntegrationPointMetrics(name=point_name)

    def record_latency(
        self,
        integration_point: str,
        latency_ms: float,
    ) -> None:
        """Record latency for an integration point.

        Args:
            integration_point: Name of the integration point
            latency_ms: Latency in milliseconds
        """
        if integration_point not in self.metrics:
            logger.warning(f"Unknown integration point: {integration_point}")
            return

        metrics = self.metrics[integration_point]
        metrics.latencies.append(latency_ms)
        # Rolling window — keep last 1000 entries to prevent unbounded growth
        if len(metrics.latencies) > 1000:
            metrics.latencies = metrics.latencies[-1000:]

        # Check if latency exceeds target
        target = self.LATENCY_TARGETS.get(integration_point, 100)
        if latency_ms > target:
            logger.warning(
                f"Latency exceeded for {integration_point}: {latency_ms:.2f}ms (target: {target}ms)"
            )

    def record_success(self, integration_point: str) -> None:
        """Record successful operation.

        Args:
            integration_point: Name of the integration point
        """
        if integration_point not in self.metrics:
            logger.warning(f"Unknown integration point: {integration_point}")
            return

        self.metrics[integration_point].success_count += 1
        self.metrics[integration_point].event_count += 1

    def record_error(
        self,
        integration_point: str,
        error: Exception,
    ) -> None:
        """Record error in integration point.

        Args:
            integration_point: Name of the integration point
            error: The error that occurred
        """
        if integration_point not in self.metrics:
            logger.warning(f"Unknown integration point: {integration_point}")
            return

        metrics = self.metrics[integration_point]
        metrics.error_count += 1
        metrics.event_count += 1
        metrics.last_error = str(error)
        metrics.last_error_time = time.time()

        logger.error(
            f"Error in {integration_point}: {error}", extra={"error_rate": metrics.error_rate}
        )

    def get_metrics(self, integration_point: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for integration point(s).

        Args:
            integration_point: Specific integration point or None for all

        Returns:
            Dictionary of metrics
        """
        if integration_point:
            if integration_point not in self.metrics:
                return {}
            return self.metrics[integration_point].to_dict()
        else:
            return {name: metrics.to_dict() for name, metrics in self.metrics.items()}

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status.

        Returns:
            Dictionary with health information
        """
        total_errors = sum(m.error_count for m in self.metrics.values())
        total_successes = sum(m.success_count for m in self.metrics.values())
        total_events = sum(m.event_count for m in self.metrics.values())

        overall_error_rate = 0.0
        if total_events > 0:
            overall_error_rate = (total_errors / total_events) * 100

        # Determine health status
        if overall_error_rate > 10:
            status = "CRITICAL"
        elif overall_error_rate > 5:
            status = "WARNING"
        else:
            status = "HEALTHY"

        return {
            "status": status,
            "overall_error_rate": overall_error_rate,
            "total_events": total_events,
            "total_errors": total_errors,
            "total_successes": total_successes,
            "uptime_seconds": time.time() - self.start_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_performance_report(self) -> Dict[str, Any]:
        """Get detailed performance report.

        Returns:
            Dictionary with performance metrics
        """
        report: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "integration_points": {},
            "summary": {
                "total_latency_samples": 0,
                "avg_latency_all": 0.0,
                "max_latency_all": 0.0,
                "points_exceeding_targets": [],
            },
        }

        all_latencies = []
        for name, metrics in self.metrics.items():
            report["integration_points"][name] = metrics.to_dict()
            all_latencies.extend(metrics.latencies)

            # Check if exceeding target
            if metrics.avg_latency > self.LATENCY_TARGETS.get(name, 100):
                report["summary"]["points_exceeding_targets"].append(
                    {
                        "point": name,
                        "avg_latency": metrics.avg_latency,
                        "target": self.LATENCY_TARGETS.get(name, 100),
                    }
                )

        if all_latencies:
            report["summary"]["total_latency_samples"] = len(all_latencies)
            report["summary"]["avg_latency_all"] = sum(all_latencies) / len(all_latencies)
            report["summary"]["max_latency_all"] = max(all_latencies)

        return report

    def export_metrics(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            Metrics in Prometheus text format
        """
        lines: list[str] = []
        lines.append(
            "# HELP divineos_integration_latency Integration point latency in milliseconds"
        )
        lines.append("# TYPE divineos_integration_latency gauge")

        for name, metrics in self.metrics.items():
            if metrics.latencies:
                lines.append(
                    f'divineos_integration_latency{{point="{name}",type="avg"}} {metrics.avg_latency}'
                )
                lines.append(
                    f'divineos_integration_latency{{point="{name}",type="max"}} {metrics.max_latency}'
                )
                lines.append(
                    f'divineos_integration_latency{{point="{name}",type="min"}} {metrics.min_latency}'
                )

        lines.append("# HELP divineos_integration_errors Integration point error count")
        lines.append("# TYPE divineos_integration_errors counter")
        for name, metrics in self.metrics.items():
            lines.append(f'divineos_integration_errors{{point="{name}"}} {metrics.error_count}')

        lines.append("# HELP divineos_integration_successes Integration point success count")
        lines.append("# TYPE divineos_integration_successes counter")
        for name, metrics in self.metrics.items():
            lines.append(
                f'divineos_integration_successes{{point="{name}"}} {metrics.success_count}'
            )

        return "\n".join(lines)


# Global monitor instance
_monitor: Optional[SystemMonitor] = None


def get_system_monitor() -> SystemMonitor:
    """Get or create the global system monitor.

    Returns:
        SystemMonitor instance
    """
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
    return _monitor


def reset_monitor() -> None:
    """Reset the global monitor (for testing)."""
    global _monitor
    _monitor = None
