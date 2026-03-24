"""Guardrails — runtime limits to prevent runaway execution.

Tracks iterations, tool calls, and token usage per session. When limits
are exceeded, returns violations that callers can act on. The guardrails
don't kill anything — they report, and the caller decides.

Severity levels:
- WARNING: approaching limit (80% threshold)
- ERROR: limit exceeded
- CRITICAL: hard limit exceeded (2x normal limit)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuardrailConfig:
    """Configuration for session guardrails."""

    max_iterations: int = 50
    max_tool_calls: int = 500
    max_tokens_per_call: int = 100_000
    max_total_tokens: int = 500_000
    tool_blocklist: list[str] = field(default_factory=list)


@dataclass
class GuardrailViolation:
    """A guardrail violation event."""

    violation_type: str  # "ITERATION", "TOOL_CALL", "TOKEN", "BLOCKED_TOOL"
    detail: str
    timestamp: float = field(default_factory=time.time)
    severity: str = "ERROR"  # "WARNING", "ERROR", "CRITICAL"


class GuardrailState:
    """Per-session guardrail tracking."""

    def __init__(self, config: GuardrailConfig | None = None) -> None:
        self.config = config or GuardrailConfig()
        self.iteration_count: int = 0
        self.tool_call_count: int = 0
        self.total_tokens: int = 0
        self.violations: list[GuardrailViolation] = []
        self._tool_call_history: list[str] = []

    def check_iteration(self) -> GuardrailViolation | None:
        """Check if iteration count is within limits."""
        if self.iteration_count >= self.config.max_iterations * 2:
            v = GuardrailViolation(
                violation_type="ITERATION",
                detail=f"Critical: {self.iteration_count} iterations (limit: {self.config.max_iterations})",
                severity="CRITICAL",
            )
            self.violations.append(v)
            return v
        if self.iteration_count >= self.config.max_iterations:
            v = GuardrailViolation(
                violation_type="ITERATION",
                detail=f"{self.iteration_count} iterations (limit: {self.config.max_iterations})",
                severity="ERROR",
            )
            self.violations.append(v)
            return v
        if self.iteration_count >= int(self.config.max_iterations * 0.8):
            v = GuardrailViolation(
                violation_type="ITERATION",
                detail=f"Approaching limit: {self.iteration_count}/{self.config.max_iterations} iterations",
                severity="WARNING",
            )
            self.violations.append(v)
            return v
        return None

    def check_tool_call(self, tool_name: str) -> GuardrailViolation | None:
        """Check if a tool call is allowed."""
        if tool_name in self.config.tool_blocklist:
            v = GuardrailViolation(
                violation_type="BLOCKED_TOOL",
                detail=f"Tool '{tool_name}' is blocklisted",
                severity="ERROR",
            )
            self.violations.append(v)
            return v

        if self.tool_call_count >= self.config.max_tool_calls * 2:
            v = GuardrailViolation(
                violation_type="TOOL_CALL",
                detail=f"Critical: {self.tool_call_count} tool calls (limit: {self.config.max_tool_calls})",
                severity="CRITICAL",
            )
            self.violations.append(v)
            return v
        if self.tool_call_count >= self.config.max_tool_calls:
            v = GuardrailViolation(
                violation_type="TOOL_CALL",
                detail=f"{self.tool_call_count} tool calls (limit: {self.config.max_tool_calls})",
                severity="ERROR",
            )
            self.violations.append(v)
            return v
        return None

    def check_tokens(self, token_count: int) -> GuardrailViolation | None:
        """Check if token usage is within limits."""
        if token_count > self.config.max_tokens_per_call:
            v = GuardrailViolation(
                violation_type="TOKEN",
                detail=f"Single call: {token_count} tokens (limit: {self.config.max_tokens_per_call})",
                severity="ERROR",
            )
            self.violations.append(v)
            return v

        if self.total_tokens + token_count > self.config.max_total_tokens * 2:
            v = GuardrailViolation(
                violation_type="TOKEN",
                detail=f"Critical total: {self.total_tokens + token_count} tokens (limit: {self.config.max_total_tokens})",
                severity="CRITICAL",
            )
            self.violations.append(v)
            return v
        if self.total_tokens + token_count > self.config.max_total_tokens:
            v = GuardrailViolation(
                violation_type="TOKEN",
                detail=f"Total: {self.total_tokens + token_count} tokens (limit: {self.config.max_total_tokens})",
                severity="ERROR",
            )
            self.violations.append(v)
            return v
        return None

    def record_iteration(self) -> None:
        """Record an iteration."""
        self.iteration_count += 1

    def record_tool_call(self, tool_name: str) -> None:
        """Record a tool call."""
        self.tool_call_count += 1
        self._tool_call_history.append(tool_name)

    def record_tokens(self, count: int) -> None:
        """Record token usage."""
        self.total_tokens += count

    def summary(self) -> dict[str, Any]:
        """Return guardrail state summary for HUD display."""
        error_count = sum(1 for v in self.violations if v.severity in ("ERROR", "CRITICAL"))
        warning_count = sum(1 for v in self.violations if v.severity == "WARNING")
        return {
            "iterations": f"{self.iteration_count}/{self.config.max_iterations}",
            "tool_calls": f"{self.tool_call_count}/{self.config.max_tool_calls}",
            "tokens": f"{self.total_tokens}/{self.config.max_total_tokens}",
            "violations": error_count,
            "warnings": warning_count,
            "status": "CRITICAL"
            if any(v.severity == "CRITICAL" for v in self.violations)
            else "ERROR"
            if error_count > 0
            else "WARNING"
            if warning_count > 0
            else "OK",
        }

    def reset(self) -> None:
        """Reset state for a new session."""
        self.iteration_count = 0
        self.tool_call_count = 0
        self.total_tokens = 0
        self.violations.clear()
        self._tool_call_history.clear()
