"""Tests for the guardrails runtime limits system."""

from divineos.core.guardrails import (
    GuardrailConfig,
    GuardrailState,
    GuardrailViolation,
)


class TestGuardrailConfig:
    def test_defaults(self):
        config = GuardrailConfig()
        assert config.max_iterations == 50
        assert config.max_tool_calls == 500
        assert config.max_tokens_per_call == 100_000
        assert config.max_total_tokens == 500_000
        assert config.tool_blocklist == []

    def test_custom_config(self):
        config = GuardrailConfig(max_iterations=10, tool_blocklist=["rm", "drop"])
        assert config.max_iterations == 10
        assert "rm" in config.tool_blocklist


class TestIterationChecks:
    def test_no_violation_under_limit(self):
        state = GuardrailState(GuardrailConfig(max_iterations=10))
        state.iteration_count = 5
        assert state.check_iteration() is None

    def test_warning_at_80_percent(self):
        state = GuardrailState(GuardrailConfig(max_iterations=10))
        state.iteration_count = 8
        v = state.check_iteration()
        assert v is not None
        assert v.severity == "WARNING"
        assert v.violation_type == "ITERATION"

    def test_error_at_limit(self):
        state = GuardrailState(GuardrailConfig(max_iterations=10))
        state.iteration_count = 10
        v = state.check_iteration()
        assert v is not None
        assert v.severity == "ERROR"

    def test_critical_at_double_limit(self):
        state = GuardrailState(GuardrailConfig(max_iterations=10))
        state.iteration_count = 20
        v = state.check_iteration()
        assert v is not None
        assert v.severity == "CRITICAL"

    def test_record_iteration(self):
        state = GuardrailState()
        assert state.iteration_count == 0
        state.record_iteration()
        assert state.iteration_count == 1
        state.record_iteration()
        assert state.iteration_count == 2


class TestToolCallChecks:
    def test_no_violation_under_limit(self):
        state = GuardrailState(GuardrailConfig(max_tool_calls=100))
        state.tool_call_count = 50
        assert state.check_tool_call("read") is None

    def test_blocklist_blocks(self):
        state = GuardrailState(GuardrailConfig(tool_blocklist=["rm", "drop_table"]))
        v = state.check_tool_call("rm")
        assert v is not None
        assert v.violation_type == "BLOCKED_TOOL"
        assert "rm" in v.detail

    def test_blocklist_allows_unlisted(self):
        state = GuardrailState(GuardrailConfig(tool_blocklist=["rm"]))
        assert state.check_tool_call("read") is None

    def test_error_at_limit(self):
        state = GuardrailState(GuardrailConfig(max_tool_calls=100))
        state.tool_call_count = 100
        v = state.check_tool_call("read")
        assert v is not None
        assert v.severity == "ERROR"

    def test_critical_at_double(self):
        state = GuardrailState(GuardrailConfig(max_tool_calls=100))
        state.tool_call_count = 200
        v = state.check_tool_call("read")
        assert v is not None
        assert v.severity == "CRITICAL"

    def test_record_tool_call(self):
        state = GuardrailState()
        state.record_tool_call("read")
        state.record_tool_call("write")
        assert state.tool_call_count == 2
        assert state._tool_call_history == ["read", "write"]


class TestTokenChecks:
    def test_no_violation_under_limits(self):
        state = GuardrailState(GuardrailConfig(max_tokens_per_call=1000, max_total_tokens=5000))
        state.total_tokens = 1000
        assert state.check_tokens(500) is None

    def test_per_call_limit(self):
        state = GuardrailState(GuardrailConfig(max_tokens_per_call=1000))
        v = state.check_tokens(1500)
        assert v is not None
        assert v.violation_type == "TOKEN"
        assert "Single call" in v.detail

    def test_total_limit(self):
        state = GuardrailState(GuardrailConfig(max_total_tokens=5000))
        state.total_tokens = 4500
        v = state.check_tokens(600)
        assert v is not None
        assert v.violation_type == "TOKEN"
        assert "Total" in v.detail

    def test_critical_total(self):
        state = GuardrailState(GuardrailConfig(max_total_tokens=5000))
        state.total_tokens = 9500
        v = state.check_tokens(600)
        assert v is not None
        assert v.severity == "CRITICAL"

    def test_record_tokens(self):
        state = GuardrailState()
        state.record_tokens(100)
        state.record_tokens(200)
        assert state.total_tokens == 300


class TestSummary:
    def test_clean_summary(self):
        state = GuardrailState(GuardrailConfig(max_iterations=50))
        state.iteration_count = 5
        state.tool_call_count = 10
        state.total_tokens = 1000
        s = state.summary()
        assert s["status"] == "OK"
        assert s["violations"] == 0
        assert s["iterations"] == "5/50"

    def test_summary_with_violations(self):
        state = GuardrailState(GuardrailConfig(max_iterations=10))
        state.iteration_count = 10
        state.check_iteration()  # triggers ERROR
        s = state.summary()
        assert s["status"] == "ERROR"
        assert s["violations"] == 1

    def test_summary_warning_only(self):
        """WARNING-only violations produce WARNING status, not OK."""
        state = GuardrailState(GuardrailConfig(max_iterations=10))
        state.iteration_count = 8  # 80% = WARNING threshold
        state.check_iteration()  # triggers WARNING
        s = state.summary()
        assert s["status"] == "WARNING"
        assert s["warnings"] == 1
        assert s["violations"] == 0  # warnings aren't errors

    def test_summary_critical_overrides(self):
        state = GuardrailState(GuardrailConfig(max_iterations=10))
        state.iteration_count = 20
        state.check_iteration()  # triggers CRITICAL
        s = state.summary()
        assert s["status"] == "CRITICAL"


class TestReset:
    def test_reset_clears_state(self):
        state = GuardrailState()
        state.record_iteration()
        state.record_tool_call("test")
        state.record_tokens(500)
        state.violations.append(GuardrailViolation(violation_type="TEST", detail="test"))

        state.reset()

        assert state.iteration_count == 0
        assert state.tool_call_count == 0
        assert state.total_tokens == 0
        assert state.violations == []
        assert state._tool_call_history == []
