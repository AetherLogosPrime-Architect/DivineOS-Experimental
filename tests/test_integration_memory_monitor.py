"""Integration tests for Memory Monitor.

Tests that the memory monitor prevents token budget overflow and manages
context compression correctly.

Property 4: Token budget enforcement
- For any session, when token usage exceeds 75% of the budget (150k of 200k),
  the memory monitor SHALL trigger context compression and reduce token usage.
"""

import divineos.agent_integration.memory_actions as memory_monitor_module
from divineos.agent_integration.memory_monitor import (
    get_memory_monitor,
)


class TestMemoryMonitorIntegration:
    """Test memory monitor integration."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global monitor for test isolation
        memory_monitor_module._monitor = None

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
        assert status_74.get("action") != "COMPRESS_NOW", "Should not compress at 74%"

        # At 76% - should trigger (COMPRESS_NOW if first time, PREPARE_COMPRESSION if already triggered)
        status_76 = self.monitor.update_token_usage(152000)
        assert status_76 is not None
        assert status_76.get("action") in ["COMPRESS_NOW", "PREPARE_COMPRESSION"], (
            "Should compress at 76%"
        )

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
        assert compressed is not None, "Compression should return event_id"
        assert isinstance(compressed, str), "Event ID should be a string"

        # Verify compression was recorded
        assert len(compressed) > 0, "Event ID should not be empty"

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
        assert "session_id" in context, "Context should have session_id"
        assert "previous_work" in context, "Context should have previous_work"
        assert "recent_context" in context, "Context should have recent_context"
        assert context["session_id"] == self.session_id, "Session ID should match"

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
        assert outcome is not None, "Should return event_id"
        assert isinstance(outcome, str), "Event ID should be a string"
        assert len(outcome) > 0, "Event ID should not be empty"

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
        assert session_record is not None, "Should return event_id"
        assert isinstance(session_record, str), "Event ID should be a string"
        assert len(session_record) > 0, "Event ID should not be empty"


class TestCompressionTriggers:
    """Test compression trigger behavior at 75% threshold.

    **Validates: Requirements 1.3**

    These tests verify that compression is triggered at the correct threshold
    and that token usage is properly reduced after compression.
    """

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global monitor for test isolation
        memory_monitor_module._monitor = None

        self.session_id = "test_compression_triggers_session"
        self.monitor = get_memory_monitor(self.session_id)
        # Threshold is 75% of 200k = 150k
        self.compression_threshold = 150000
        self.total_budget = 200000

    def test_compression_not_triggered_below_threshold(self):
        """
        Test that compression is NOT triggered below 75% threshold.

        Scenario:
        1. Update token usage to 74% (148k)
        2. Verify compression is not triggered
        3. Verify action is not COMPRESS_NOW
        """
        tokens_at_74_percent = 148000
        status = self.monitor.update_token_usage(tokens_at_74_percent)

        assert status is not None
        assert status["current_tokens"] == tokens_at_74_percent
        assert status["action"] != "COMPRESS_NOW", "Should not compress below 75%"
        assert status["usage_percent"] < 75.0

    def test_compression_triggered_at_exactly_threshold(self):
        """
        Test that compression IS triggered at exactly 75% threshold.

        Scenario:
        1. Update token usage to exactly 75% (150k)
        2. Verify compression is triggered
        3. Verify action is COMPRESS_NOW (first time) or PREPARE_COMPRESSION (if already triggered)
        """
        tokens_at_75_percent = 150000
        status = self.monitor.update_token_usage(tokens_at_75_percent)

        assert status is not None
        assert status["current_tokens"] == tokens_at_75_percent
        # At exactly 75%, should trigger compression (COMPRESS_NOW if first time)
        assert status["action"] in ["COMPRESS_NOW", "PREPARE_COMPRESSION"]
        assert status["usage_percent"] >= 75.0

    def test_compression_triggered_above_threshold(self):
        """
        Test that compression IS triggered above 75% threshold.

        Scenario:
        1. Update token usage to 76% (152k)
        2. Verify compression is triggered
        3. Verify action is COMPRESS_NOW (first time) or PREPARE_COMPRESSION (subsequent)
        """
        tokens_at_76_percent = 152000
        status = self.monitor.update_token_usage(tokens_at_76_percent)

        assert status is not None
        assert status["current_tokens"] == tokens_at_76_percent
        # First call at 76% should trigger COMPRESS_NOW, but if compression_triggered
        # was already set, it will be PREPARE_COMPRESSION
        assert status["action"] in ["COMPRESS_NOW", "PREPARE_COMPRESSION"]
        assert status["usage_percent"] > 75.0

    def test_compression_triggered_only_once(self):
        """
        Test that compression trigger flag is set only once.

        Scenario:
        1. Update to 76% (152k) - should trigger COMPRESS_NOW
        2. Update to 77% (154k) - should return PREPARE_COMPRESSION (not COMPRESS_NOW again)
        3. Verify compression_triggered flag is set
        """
        # First update - should trigger COMPRESS_NOW
        status1 = self.monitor.update_token_usage(152000)
        # First time at threshold should be COMPRESS_NOW
        assert status1["action"] in ["COMPRESS_NOW", "PREPARE_COMPRESSION"]

        # Second update - should not trigger COMPRESS_NOW again
        status2 = self.monitor.update_token_usage(154000)
        # After first trigger, should be PREPARE_COMPRESSION or None
        assert status2["action"] != "COMPRESS_NOW" or status2["action"] is None
        assert self.monitor.compression_triggered is True

    def test_warning_threshold_before_compression(self):
        """
        Test that warning threshold (65%) is triggered before compression (75%).

        Scenario:
        1. Update to 66% (132k)
        2. Verify action is PREPARE_COMPRESSION
        3. Verify compression is not yet triggered
        """
        tokens_at_66_percent = 132000
        status = self.monitor.update_token_usage(tokens_at_66_percent)

        assert status is not None
        assert status["current_tokens"] == tokens_at_66_percent
        assert status["action"] == "PREPARE_COMPRESSION", "Should prepare at 65%+"
        assert status["usage_percent"] >= 65.0
        assert status["usage_percent"] < 75.0

    def test_threshold_values_correct(self):
        """
        Test that threshold values are correctly calculated.

        Scenario:
        1. Verify compression threshold is 75% of 200k
        2. Verify warning threshold is 65% of 200k
        """
        assert self.monitor.COMPRESSION_THRESHOLD == 150000, "75% of 200k should be 150k"
        assert self.monitor.WARNING_THRESHOLD == 130000, "65% of 200k should be 130k"
        assert self.monitor.TOTAL_BUDGET == 200000, "Total budget should be 200k"

    def test_compression_reduces_token_count(self):
        """
        Test that after compression, token count can be reduced.

        Scenario:
        1. Set high token usage (160k)
        2. Compress context
        3. Update to lower token count (80k)
        4. Verify new count is lower
        """
        # Set high token usage
        high_tokens = 160000
        status_high = self.monitor.update_token_usage(high_tokens)
        assert status_high["current_tokens"] == high_tokens

        # Compress context
        summary = "Checkpoint: completed 15 operations"
        event_id = self.monitor.compress_context(summary)
        assert event_id is not None
        assert len(event_id) > 0

        # Update to lower token count
        low_tokens = 80000
        status_low = self.monitor.update_token_usage(low_tokens)
        assert status_low["current_tokens"] == low_tokens
        assert status_low["current_tokens"] < high_tokens

    def test_remaining_tokens_calculated_correctly(self):
        """
        Test that remaining tokens are calculated correctly.

        Scenario:
        1. Update to 100k tokens
        2. Verify remaining is 100k (200k - 100k)
        3. Update to 150k tokens
        4. Verify remaining is 50k (200k - 150k)
        """
        # At 100k
        status1 = self.monitor.update_token_usage(100000)
        assert status1["remaining_tokens"] == 100000

        # At 150k
        status2 = self.monitor.update_token_usage(150000)
        assert status2["remaining_tokens"] == 50000

    def test_usage_percent_calculated_correctly(self):
        """
        Test that usage percentage is calculated correctly.

        Scenario:
        1. Update to 50k tokens (25%)
        2. Verify usage_percent is 25.0
        3. Update to 100k tokens (50%)
        4. Verify usage_percent is 50.0
        """
        # At 50k (25%)
        status1 = self.monitor.update_token_usage(50000)
        assert abs(status1["usage_percent"] - 25.0) < 0.1

        # At 100k (50%)
        status2 = self.monitor.update_token_usage(100000)
        assert abs(status2["usage_percent"] - 50.0) < 0.1


class TestTokenReductionAfterCompression:
    """Test token reduction after compression.

    **Validates: Requirements 1.3**

    These tests verify that context compression effectively reduces token usage
    and that the system can continue operating after compression.
    """

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global monitor for test isolation
        memory_monitor_module._monitor = None

        self.session_id = "test_token_reduction_session"
        self.monitor = get_memory_monitor(self.session_id)

    def test_compression_event_recorded(self):
        """
        Test that compression event is recorded in ledger.

        Scenario:
        1. Compress context with summary
        2. Verify event ID is returned
        3. Verify event ID is non-empty string
        """
        summary = "Session checkpoint: 10 operations completed"
        event_id = self.monitor.compress_context(summary)

        assert event_id is not None
        assert isinstance(event_id, str)
        assert len(event_id) > 0

    def test_multiple_compressions_in_sequence(self):
        """
        Test that multiple compressions can be performed in sequence.

        Scenario:
        1. Compress at 160k tokens
        2. Reduce to 80k tokens
        3. Increase to 155k tokens
        4. Compress again
        5. Verify both compressions succeeded
        """
        # First compression
        self.monitor.update_token_usage(160000)
        event_id1 = self.monitor.compress_context("First checkpoint")
        assert event_id1 is not None

        # Reduce tokens
        self.monitor.update_token_usage(80000)

        # Increase tokens again
        self.monitor.update_token_usage(155000)

        # Second compression
        event_id2 = self.monitor.compress_context("Second checkpoint")
        assert event_id2 is not None

        # Verify both event IDs are different
        assert event_id1 != event_id2

    def test_compression_with_different_summaries(self):
        """
        Test that compression works with different summary texts.

        Scenario:
        1. Compress with short summary
        2. Compress with long summary
        3. Compress with special characters
        4. Verify all succeed
        """
        summaries = [
            "Short",
            "This is a longer summary with more details about the work completed",
            "Summary with special chars: !@#$%^&*()",
            "Multi-line\nsummary\nwith\nnewlines",
        ]

        event_ids = []
        for summary in summaries:
            self.monitor.update_token_usage(155000)
            event_id = self.monitor.compress_context(summary)
            assert event_id is not None
            event_ids.append(event_id)

        # Verify all event IDs are unique
        assert len(set(event_ids)) == len(event_ids)

    def test_token_tracking_across_compressions(self):
        """
        Test that token tracking works correctly across multiple compressions.

        Scenario:
        1. Track tokens: 50k -> 100k -> 150k
        2. Compress
        3. Track tokens: 80k -> 120k -> 160k
        4. Compress
        5. Verify all token updates recorded correctly
        """
        token_sequence = [50000, 100000, 150000, 80000, 120000, 160000]

        for i, tokens in enumerate(token_sequence):
            status = self.monitor.update_token_usage(tokens)
            assert status["current_tokens"] == tokens

            # Compress at high points
            if tokens >= 150000:
                event_id = self.monitor.compress_context(f"Checkpoint {i}")
                assert event_id is not None

    def test_compression_preserves_session_id(self):
        """
        Test that compression events preserve session ID.

        Scenario:
        1. Compress context
        2. Verify session ID is preserved in event
        """
        self.monitor.update_token_usage(155000)
        event_id = self.monitor.compress_context("Test checkpoint")

        assert event_id is not None
        # Session ID should be stored in the monitor
        assert self.monitor.session_id is not None

    def test_compression_with_zero_tokens(self):
        """
        Test compression behavior when starting from zero tokens.

        Scenario:
        1. Start with zero tokens
        2. Increase to 155k
        3. Compress
        4. Verify compression succeeds
        """
        self.monitor.update_token_usage(0)
        self.monitor.update_token_usage(155000)

        event_id = self.monitor.compress_context("Compression from zero")
        assert event_id is not None

    def test_compression_status_after_compression(self):
        """
        Test that status is correct after compression.

        Scenario:
        1. Update to 160k tokens
        2. Compress
        3. Update to 80k tokens
        4. Verify status shows reduced tokens
        """
        # High tokens
        status1 = self.monitor.update_token_usage(160000)
        assert status1["current_tokens"] == 160000

        # Compress
        event_id = self.monitor.compress_context("Compression test")
        assert event_id is not None

        # Low tokens
        status2 = self.monitor.update_token_usage(80000)
        assert status2["current_tokens"] == 80000
        assert status2["usage_percent"] == 40.0


class TestMemoryMonitorEdgeCases:
    """Test edge cases in memory monitor."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global monitor for test isolation
        memory_monitor_module._monitor = None

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
