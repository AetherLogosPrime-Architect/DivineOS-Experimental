"""Type definitions and data models for Kiro Agent Integration.

Defines all data structures used across the agent integration system,
including event payloads, analysis results, and configuration objects.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ToolCallEvent:
    """Represents a TOOL_CALL event for agent tool invocation."""

    tool_name: str
    tool_input: dict[str, Any]
    tool_use_id: str
    session_id: str
    timestamp: str  # ISO8601 format
    explanation: str
    actor: str = "assistant"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for ledger storage."""
        return {
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_use_id": self.tool_use_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "explanation": self.explanation,
            "actor": self.actor,
        }


@dataclass
class ToolResultEvent:
    """Represents a TOOL_RESULT event for agent tool execution result."""

    tool_name: str
    tool_use_id: str
    result: str
    duration_ms: int
    session_id: str
    timestamp: str  # ISO8601 format
    failed: bool = False
    error_message: str | None = None
    actor: str = "assistant"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for ledger storage."""
        return {
            "tool_name": self.tool_name,
            "tool_use_id": self.tool_use_id,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "failed": self.failed,
            "error_message": self.error_message,
            "actor": self.actor,
        }


@dataclass
class Correction:
    """Represents a correction lesson (mistake made and fixed)."""

    tool_name: str
    error_message: str
    fixed: bool
    session_id: str
    timestamp: str


@dataclass
class Encouragement:
    """Represents an encouragement lesson (successful pattern)."""

    description: str
    tool_names: list[str]
    success_count: int
    session_id: str
    timestamp: str


@dataclass
class Decision:
    """Represents a decision lesson (explicit choice made)."""

    description: str
    context: str
    outcome: str
    session_id: str
    timestamp: str


@dataclass
class ToolPattern:
    """Represents a tool usage pattern."""

    tool_name: str
    call_count: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float


@dataclass
class TimingPattern:
    """Represents timing patterns for tools."""

    tool_name: str
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    median_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float


@dataclass
class ErrorPattern:
    """Represents error patterns for tools."""

    tool_name: str
    error_count: int
    error_types: dict[str, int]
    most_common_error: str
    error_rate: float


@dataclass
class SessionLessons:
    """Represents all lessons extracted from a session."""

    session_id: str
    corrections: list[Correction] = field(default_factory=list)
    encouragements: list[Encouragement] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    tool_patterns: dict[str, ToolPattern] = field(default_factory=dict)
    timing_patterns: dict[str, TimingPattern] = field(default_factory=dict)
    error_patterns: dict[str, ErrorPattern] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class BehaviorAnalysis:
    """Represents behavior analysis results for a session."""

    session_id: str
    tool_frequency: dict[str, int]
    success_rates: dict[str, float]
    execution_times: dict[str, dict[str, float]]
    error_patterns: dict[str, dict[str, Any]]
    correction_patterns: dict[str, int]
    decision_patterns: dict[str, int]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SessionFeedback:
    """Represents feedback for a completed session."""

    session_id: str
    tool_usage: dict[str, int]
    success_rates: dict[str, float]
    timing: dict[str, dict[str, float]]
    errors: list[str]
    lessons_learned: list[str]
    recommendations: list[str]
    improvements: list[str]
    regressions: list[str]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for knowledge entry storage."""
        return {
            "session_id": self.session_id,
            "tool_usage": self.tool_usage,
            "success_rates": self.success_rates,
            "timing": self.timing,
            "errors": self.errors,
            "lessons_learned": self.lessons_learned,
            "recommendations": self.recommendations,
            "improvements": self.improvements,
            "regressions": self.regressions,
        }


# Set of internal tools that should not be captured
INTERNAL_TOOLS: set[str] = {
    "emit_tool_call",
    "emit_tool_result",
    "emit_explanation",
    "get_session_id",
    "get_agent_session_id",
    "read_session_file",
    "write_session_file",
    "log_event",
    "get_events",
    "verify_event_hash",
    "store_event",
    "search_events",
    "count_events",
    "get_recent_context",
    "verify_all_events",
    "clean_corrupted_events",
    "export_to_markdown",
    "store_knowledge",
    "get_knowledge",
    "update_knowledge",
    "generate_briefing",
    "knowledge_stats",
    "rebuild_fts_index",
    "get_lesson_summary",
    "get_lessons",
    "deep_extract_knowledge",
    "consolidate_related",
    "apply_session_feedback",
    "health_check",
    "knowledge_health_report",
    "clear_lessons",
    "migrate_knowledge_types",
    "set_core",
    "clear_core",
    "format_core",
    "promote_to_active",
    "get_active_memory",
    "refresh_active_memory",
    "recall",
    "format_recall",
    "run_all_features",
    "store_features",
    "get_cross_session_summary",
    "analyze_session",
    "format_analysis_report",
    "store_analysis",
}
