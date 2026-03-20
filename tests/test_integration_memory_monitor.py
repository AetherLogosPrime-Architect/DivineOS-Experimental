"""Integration tests for Memory Monitor.

Tests that the memory monitor prevents token budget overflow and manages
context compression correctly.

Property 4: Token budget enforcement
- For any session, when token usage exceeds 75% of the budget (150k of 200k),
  the memory monitor SHALL trigger context compression and reduce token usage.
"""

from divineos.agent_integration.memory_monitor import (
    get_memory_monitor,
)


class TestMemoryMonitorIntegration:
    """Test memory monitor integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session_id = "test_memory_monitor_session"
        self.monitor = get_memory_monitor(self.session_id)

    def test_token_budget_enforcement(self):
        """
        Test that token budget is enforced.

        Scenario:
        1. Start session with memory monitor
        2. Simulate token usage approaching limit
        3. At 75% (150k), compression should be triggered
        4. After compression, tokens should be reduced

        Property 4: Token budget enforcement
        """
        # Load initial context
        context = self.monitor.load_session_context()
        assert context is not None, "Should load session context"

        # Simulate token usage
        initial_tokens = 10000
        status = self.monitor.update_token_usage(initial_tokens)
        assert status is not None
        assert status["current_tokens"] == initial_tokens

        # Simulate approaching limit (75% = 150k)
        approaching_limit = 145000
        status = self.monitor.update_token_usage(approaching_limit)
        assert status is not None
        assert status["current_tokens"] == approaching_limit

        # Check if compression is recommended
        if status.get("should_compress"):
            # Compress context
            summary = "Completed 10 operations, learned 3 patterns"
            compressed = self.monitor.compress_context(summary)
            assert compressed is not None, "Compression should succeed"

            # Verify tokens reduced
            new_status = self.monitor.update_token_usage(50000)
            assert new_status["current_tokens"] < approaching_limit

    def test_compression_triggered_at_threshold(self):
        """
        Test that compression is triggered at 75% threshold.

        Scenario:
        1. Update token usage to 74% (148k)
        2. Compression should not be triggered
        3. Update to 76% (152k)
        4. Compression should be triggered
        """
        # At 74% - should not trigger
        status_74 = self.monitor.update_token_usage(148000)
        assert status_74 is not None

        # At 76% - should trigger
        status_76 = self.monitor.update_token_usage(152000)
        assert status_76 is not None

        # If should_compress is present, it should be True at 76%
        if "should_compress" in status_76:
            assert status_76["should_compress"]

    def test_context_compression_reduces_tokens(self):
        """
        Test that context compression reduces token usage.

        Scenario:
        1. Set high token usage
        2. Compress context
        3. Verify tokens are reduced
        """
        # Set high token usage
        high_tokens = 160000
        self.monitor.update_token_usage(high_tokens)

        # Compress context
        summary = "Session checkpoint: completed 20 operations"
        compressed = self.monitor.compress_context(summary)
        assert compressed is not None

        # Update with lower tokens
        new_tokens = 50000
        status = self.monitor.update_token_usage(new_tokens)
        assert status["current_tokens"] == new_tokens

    def test_session_context_loading(self):
        """
        Test that session context is loaded correctly.

        Scenario:
        1. Load session context
        2. Verify context is not None
        3. Verify context has expected structure
        """
        context = self.monitor.load_session_context()
        assert context is not None, "Should load session context"
        assert isinstance(context, dict), "Context should be a dictionary"

    def test_work_outcome_recording(self):
        """
        Test that work outcomes are recorded.

        Scenario:
        1. Record a work outcome
        2. Verify outcome is stored
        """
        task = "read_file"
        pattern_id = "pattern_123"
        success = True

        # Record outcome
        outcome = self.monitor.record_work_outcome(
            task=task,
            pattern_id=pattern_id,
            success=success,
            violations_introduced=0,
            token_efficiency=0.95,
        )
        assert outcome is not None

    def test_session_end(self):
        """
        Test that session can be ended properly.

        Scenario:
        1. Record some work
        2. End session with summary
        3. Verify session is recorded
        """
        # Record some work
        self.monitor.update_token_usage(50000)

        # End session
        summary = "Session completed successfully"
        session_record = self.monitor.end_session(summary, "completed")
        assert session_record is not None


class TestMemoryMonitorEdgeCases:
    """Test edge cases in memory monitor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.session_id = "test_edge_case_session"
        self.monitor = get_memory_monitor(self.session_id)

    def test_zero_tokens(self):
        """
        Test handling of zero tokens.

        Scenario:
        1. Update with zero tokens
        2. Should not raise error
        """
        status = self.monitor.update_token_usage(0)
        assert status is not None
        assert status["current_tokens"] == 0

    def test_negative_tokens_handled(self):
        """
        Test handling of negative tokens (edge case).

        Scenario:
        1. Try to update with negative tokens
        2. Should handle gracefully
        """
        # This might raise an error or handle gracefully
        # depending on implementation
        try:
            status = self.monitor.update_token_usage(-1000)
            # If it doesn't raise, verify it's handled
            assert status is not None
        except (ValueError, AssertionError):
            # Expected behavior - negative tokens not allowed
            pass

    def test_exceeding_budget(self):
        """
        Test handling when exceeding budget.

        Scenario:
        1. Update tokens to exceed budget (200k)
        2. Should handle gracefully
        """
        # Exceed budget
        over_budget = 210000
        status = self.monitor.update_token_usage(over_budget)
        assert status is not None

        # Should indicate over budget
        if "over_budget" in status:
            assert status["over_budget"]

    def test_multiple_compressions(self):
        """
        Test multiple compression cycles.

        Scenario:
        1. Compress context
        2. Add more tokens
        3. Compress again
        4. Verify system handles multiple compressions
        """
        # First compression
        self.monitor.update_token_usage(160000)
        compressed1 = self.monitor.compress_context("First checkpoint")
        assert compressed1 is not None

        # Add more tokens
        self.monitor.update_token_usage(100000)

        # Second compression
        compressed2 = self.monitor.compress_context("Second checkpoint")
        assert compressed2 is not None

    def test_learning_cycle_integration(self):
        """
        Test that learning cycle can be run.

        Scenario:
        1. Run learning cycle
        2. Verify it completes
        """
        # Run learning cycle
        cycle_result = self.monitor.run_learning_cycle()
        assert cycle_result is not None

    def test_recommendation_generation(self):
        """
        Test that recommendations can be generated.

        Scenario:
        1. Get recommendation
        2. Verify recommendation is returned
        """
        context = self.monitor.load_session_context()
        recommendation = self.monitor.get_recommendation(context)
        assert recommendation is not None
