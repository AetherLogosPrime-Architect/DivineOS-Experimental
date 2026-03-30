"""Tests for the session checkpoint system — periodic saves and context monitoring."""

import json

from divineos.core.session_checkpoint import (
    CHECKPOINT_EDIT_THRESHOLD,
    CONTEXT_CRITICAL_THRESHOLD,
    CONTEXT_URGENT_THRESHOLD,
    CONTEXT_WARN_THRESHOLD,
    _counter_path,
    _load_state,
    _save_state,
    context_warning_level,
    format_context_warning,
    increment_edit,
    increment_tool_call,
    reset_state,
    should_checkpoint,
)


class TestCheckpointState:
    def setup_method(self):
        """Reset state before each test."""
        reset_state()

    def test_reset_state_zeros_counters(self):
        state = _load_state()
        assert state["edits"] == 0
        assert state["tool_calls"] == 0
        assert state["checkpoints_run"] == 0

    def test_increment_edit_counts_both(self):
        state = increment_edit()
        assert state["edits"] == 1
        assert state["tool_calls"] == 1  # edits are also tool calls

    def test_increment_tool_call_only_counts_calls(self):
        state = increment_tool_call()
        assert state["edits"] == 0
        assert state["tool_calls"] == 1

    def test_multiple_increments_accumulate(self):
        for _ in range(5):
            increment_edit()
        for _ in range(3):
            increment_tool_call()
        state = _load_state()
        assert state["edits"] == 5
        assert state["tool_calls"] == 8  # 5 edits + 3 tool calls

    def test_state_persists_to_disk(self):
        increment_edit()
        path = _counter_path()
        assert path.exists()
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["edits"] == 1


class TestCheckpointDecision:
    def setup_method(self):
        reset_state()

    def test_no_checkpoint_before_threshold(self):
        for _ in range(CHECKPOINT_EDIT_THRESHOLD - 1):
            state = increment_edit()
        assert not should_checkpoint(state)

    def test_checkpoint_at_threshold(self):
        for _ in range(CHECKPOINT_EDIT_THRESHOLD):
            state = increment_edit()
        assert should_checkpoint(state)

    def test_checkpoint_resets_after_run(self):
        for _ in range(CHECKPOINT_EDIT_THRESHOLD):
            increment_edit()
        state = _load_state()
        state["checkpoints_run"] = 1
        _save_state(state)
        assert not should_checkpoint(state)

    def test_second_checkpoint_after_more_edits(self):
        state = _load_state()
        state["edits"] = CHECKPOINT_EDIT_THRESHOLD * 2
        state["checkpoints_run"] = 1
        _save_state(state)
        assert should_checkpoint(state)


class TestContextMonitoring:
    def test_ok_level_below_threshold(self):
        assert context_warning_level({"tool_calls": 50}) == "ok"

    def test_warn_at_threshold(self):
        assert context_warning_level({"tool_calls": CONTEXT_WARN_THRESHOLD}) == "warn"

    def test_urgent_at_threshold(self):
        assert context_warning_level({"tool_calls": CONTEXT_URGENT_THRESHOLD}) == "urgent"

    def test_critical_at_threshold(self):
        assert context_warning_level({"tool_calls": CONTEXT_CRITICAL_THRESHOLD}) == "critical"

    def test_no_warning_when_ok(self):
        assert format_context_warning({"tool_calls": 10}) is None

    def test_warning_contains_counts(self):
        warning = format_context_warning({"tool_calls": 160, "edits": 20, "checkpoints_run": 1})
        assert warning is not None
        assert "160" in warning
        assert "20" in warning

    def test_urgent_warning_mentions_session_end(self):
        warning = format_context_warning({"tool_calls": 260, "edits": 30, "checkpoints_run": 2})
        assert warning is not None
        assert "SESSION_END" in warning
        assert "HIGH" in warning

    def test_critical_warning_mentions_imminent(self):
        warning = format_context_warning({"tool_calls": 360, "edits": 40, "checkpoints_run": 3})
        assert warning is not None
        assert "CRITICAL" in warning
        assert "imminent" in warning
