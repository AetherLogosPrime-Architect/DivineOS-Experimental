"""
Performance tests for DivineOS system.

Measures and validates performance characteristics:
- Tool call latency
- Ledger write throughput
- Learning analysis performance
- Memory compression efficiency

Property 10: Performance latency
- Tool calls complete within acceptable time
- Ledger operations scale linearly
- Memory operations are efficient
"""

import pytest
import time
from datetime import datetime, timezone

from hypothesis_compat import HAS_HYPOTHESIS, given, st, settings, HealthCheck


from divineos.clarity_enforcement.config import ClarityConfig, ClarityEnforcementMode
from divineos.clarity_enforcement.enforcer import ClarityEnforcer
from divineos.core.ledger import Ledger
from divineos.core.session_manager import initialize_session, end_session as end_session_manager
from divineos.agent_integration.memory_monitor import get_memory_monitor
from divineos.supersession.contradiction_detector import ContradictionDetector

# Skip all tests in this module if hypothesis is not installed
pytestmark = pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")


class TestToolCallLatency:
    """Test tool call latency performance."""

    @pytest.fixture
    def setup(self):
        """Set up test environment."""
        self.session_id = initialize_session()
        self.memory_monitor = get_memory_monitor(self.session_id)
        yield
        # End session via memory monitor to trigger learning cycle
        try:
            self.memory_monitor.end_session("Performance test completed")
        except Exception:
            pass
        # Also end session manager
        try:
            end_session_manager()
        except Exception:
            pass

    def test_token_update_latency(self, setup):
        """Test token update latency."""
        start = time.perf_counter()
        for _ in range(100):
            self.memory_monitor.update_token_usage(10000)
        elapsed = time.perf_counter() - start

        # Should complete 100 updates in < 100ms
        assert elapsed < 0.1, f"Token updates took {elapsed:.3f}s, expected < 0.1s"

    def test_session_context_load_latency(self, setup):
        """Test session context load latency."""
        start = time.perf_counter()
        for _ in range(50):
            context = self.memory_monitor.load_session_context()
            assert context is not None
        elapsed = time.perf_counter() - start

        # Should complete 50 loads in < 200ms (ledger queries take time)
        assert elapsed < 0.2, f"Context loads took {elapsed:.3f}s, expected < 0.2s"

    def test_checkpoint_save_latency(self, setup):
        """Test checkpoint save latency."""
        start = time.perf_counter()
        for i in range(10):
            checkpoint = self.memory_monitor.save_work_checkpoint(
                task=f"Task {i}",
                status="completed",
                files_modified=[f"file_{i}.py"],
                tests_passing=10,
            )
            assert checkpoint is not None
        elapsed = time.perf_counter() - start

        # Should complete 10 checkpoints in < 500ms
        assert elapsed < 0.5, f"Checkpoints took {elapsed:.3f}s, expected < 0.5s"


class TestLedgerWriteThroughput:
    """Test ledger write throughput."""

    @pytest.fixture
    def setup(self):
        """Set up test environment."""
        self.ledger = Ledger()
        yield

    def test_fact_storage_throughput(self, setup):
        """Test fact storage throughput."""
        start = time.perf_counter()
        for i in range(100):
            fact = {
                "id": f"fact-{i}",
                "content": f"Fact {i}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.95,
            }
            self.ledger.store_fact(fact)
        elapsed = time.perf_counter() - start

        # Should store 100 facts in < 1 second
        assert elapsed < 1.0, f"Fact storage took {elapsed:.3f}s, expected < 1.0s"

        # Verify throughput
        throughput = 100 / elapsed
        assert throughput > 100, f"Throughput {throughput:.0f} facts/sec, expected > 100"

    def test_event_logging_throughput(self, setup):
        """Test event logging throughput."""
        start = time.perf_counter()
        for i in range(100):
            event = {
                "event_type": "TEST_EVENT",
                "actor": "test",
                "payload": {"index": i, "data": f"Event {i}"},
            }
            self.ledger.log_event(
                event_type=event["event_type"], actor=event["actor"], payload=event["payload"]
            )
        elapsed = time.perf_counter() - start

        # Should log 100 events in < 1 second
        assert elapsed < 1.0, f"Event logging took {elapsed:.3f}s, expected < 1.0s"

        # Verify throughput
        throughput = 100 / elapsed
        assert throughput > 100, f"Throughput {throughput:.0f} events/sec, expected > 100"


class TestMemoryCompressionEfficiency:
    """Test memory compression efficiency."""

    @pytest.fixture
    def setup(self):
        """Set up test environment."""
        self.session_id = initialize_session()
        self.memory_monitor = get_memory_monitor(self.session_id)
        yield
        # End session via memory monitor to trigger learning cycle
        try:
            self.memory_monitor.end_session("Memory compression test completed")
        except Exception:
            pass
        # Also end session manager
        try:
            end_session_manager()
        except Exception:
            pass

    def test_compression_speed(self, setup):
        """Test compression speed."""
        # Accumulate some tokens
        for _ in range(10):
            self.memory_monitor.update_token_usage(10000)

        start = time.perf_counter()
        compressed = self.memory_monitor.compress_context("Test compression")
        elapsed = time.perf_counter() - start

        # Compression should complete in < 100ms
        assert elapsed < 0.1, f"Compression took {elapsed:.3f}s, expected < 0.1s"
        assert compressed is not None

    def test_learning_cycle_performance(self, setup):
        """Test learning cycle performance."""
        start = time.perf_counter()
        learning = self.memory_monitor.run_learning_cycle()
        elapsed = time.perf_counter() - start

        # Learning cycle should complete in < 500ms
        assert elapsed < 0.5, f"Learning cycle took {elapsed:.3f}s, expected < 0.5s"
        assert learning is not None


class TestClarityEnforcementPerformance:
    """Test clarity enforcement performance."""

    @pytest.fixture
    def setup(self):
        """Set up test environment."""
        self.config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        self.enforcer = ClarityEnforcer(self.config)
        yield

    def test_enforcer_initialization_latency(self, setup):
        """Test enforcer initialization latency."""
        start = time.perf_counter()
        for _ in range(100):
            config = ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.LOGGING,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
            ClarityEnforcer(config)
        elapsed = time.perf_counter() - start

        # Should initialize 100 enforcers in < 100ms
        assert elapsed < 0.1, f"Enforcer init took {elapsed:.3f}s, expected < 0.1s"


class TestContradictionDetectionPerformance:
    """Test contradiction detection performance."""

    @pytest.fixture
    def setup(self):
        """Set up test environment."""
        self.detector = ContradictionDetector()
        yield

    def test_contradiction_detection_latency(self, setup):
        """Test contradiction detection latency."""
        fact_1 = {
            "id": "fact-1",
            "content": "API returns JSON",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": 0.95,
        }

        fact_2 = {
            "id": "fact-2",
            "content": "API returns XML",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": 0.90,
        }

        start = time.perf_counter()
        for _ in range(100):
            self.detector.detect_contradiction(fact_1, fact_2)
        elapsed = time.perf_counter() - start

        # Should detect 100 contradictions in < 100ms
        assert elapsed < 0.1, f"Contradiction detection took {elapsed:.3f}s, expected < 0.1s"


class TestScalability:
    """Test system scalability."""

    @pytest.fixture
    def setup(self):
        """Set up test environment."""
        self.ledger = Ledger()
        yield

    def test_ledger_scalability_with_facts(self, setup):
        """Test ledger scalability with increasing fact count."""
        # Store facts in batches and measure time
        batch_sizes = [10, 50, 100]
        times = []

        for batch_size in batch_sizes:
            start = time.perf_counter()
            for i in range(batch_size):
                fact = {
                    "id": f"fact-{len(times)}-{i}",
                    "content": f"Fact {i}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "confidence": 0.95,
                }
                self.ledger.store_fact(fact)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        # Verify linear scaling (time should increase roughly linearly)
        # Allow for some variance
        ratio_1 = times[1] / times[0]  # Should be ~5
        ratio_2 = times[2] / times[1]  # Should be ~2

        # Both ratios should be close to expected (within 2x)
        assert ratio_1 < 10, f"Scaling ratio {ratio_1:.1f} indicates non-linear behavior"
        assert ratio_2 < 5, f"Scaling ratio {ratio_2:.1f} indicates non-linear behavior"


@given(
    operation_count=st.integers(min_value=10, max_value=100),
    token_amount=st.integers(min_value=5000, max_value=50000),
)
@pytest.mark.slow
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_property_performance_latency(operation_count, token_amount):
    """
    Property 10: Performance latency

    For any sequence of operations:
    - Operations complete within acceptable time
    - Throughput is consistent
    - No performance degradation
    """
    session_id = initialize_session()
    memory_monitor = get_memory_monitor(session_id)

    try:
        start = time.perf_counter()
        for i in range(operation_count):
            memory_monitor.update_token_usage(token_amount)
        elapsed = time.perf_counter() - start

        # Should complete operations in reasonable time
        # Allow ~1ms per operation
        max_time = operation_count * 0.001
        assert elapsed < max_time, f"Operations took {elapsed:.3f}s, expected < {max_time:.3f}s"

        # Verify throughput
        throughput = operation_count / elapsed
        assert throughput > 100, f"Throughput {throughput:.0f} ops/sec, expected > 100"

    finally:
        # End session via memory monitor
        try:
            memory_monitor.end_session("Property test completed")
        except Exception:
            pass
        # Also end session manager
        try:
            end_session_manager()
        except Exception:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
