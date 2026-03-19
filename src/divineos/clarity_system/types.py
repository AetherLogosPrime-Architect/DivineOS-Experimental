"""Type definitions for Agent Work Clarity System.

Defines all data structures used across the clarity system,
including clarity statements, plans, execution data, deviations, lessons, and summaries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass
class ScopeEstimate:
    """Estimated scope for planned work."""

    estimated_files: int
    estimated_tool_calls: int
    estimated_complexity: str  # low, medium, high
    estimated_time_minutes: int


@dataclass
class ClarityStatement:
    """Pre-work clarity statement describing planned work."""

    id: UUID = field(default_factory=uuid4)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    goal: str = ""
    approach: str = ""
    expected_outcome: str = ""
    scope: ScopeEstimate = field(default_factory=lambda: ScopeEstimate(0, 0, "medium", 0))
    user_feedback: str | None = None


@dataclass
class PlanMetrics:
    """Metrics extracted from plan."""

    estimated_files: int
    estimated_tool_calls: int
    estimated_complexity: str
    estimated_time_minutes: int


@dataclass
class PlanData:
    """Structured plan data extracted from clarity statement."""

    clarity_statement_id: UUID
    goal: str
    approach: str
    expected_outcome: str
    metrics: PlanMetrics


@dataclass
class ToolCall:
    """A tool call event from the ledger."""

    tool_name: str
    timestamp: str
    input: dict[str, Any]


@dataclass
class ExecutionMetrics:
    """Metrics calculated from actual execution."""

    actual_files: int
    actual_tool_calls: int
    actual_errors: int
    actual_time_minutes: float
    success_rate: float


@dataclass
class ExecutionData:
    """Actual execution data extracted from ledger."""

    session_id: UUID
    tool_calls: list[ToolCall] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metrics: ExecutionMetrics = field(default_factory=lambda: ExecutionMetrics(0, 0, 0, 0.0, 0.0))


@dataclass
class Deviation:
    """A deviation between planned and actual metrics."""

    metric: str
    planned: float
    actual: float
    difference: float
    percentage: float
    severity: str  # low, medium, high
    category: str  # scope, efficiency, quality, approach


@dataclass
class Lesson:
    """A lesson extracted from execution."""

    id: UUID = field(default_factory=uuid4)
    type: str = ""  # deviation, pattern, error_pattern, approach
    description: str = ""
    context: str = ""
    insight: str = ""
    confidence: float = 0.0
    source_session_id: UUID | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Recommendation:
    """A recommendation generated from lessons."""

    lesson_id: UUID
    recommendation_text: str
    priority: str  # low, medium, high
    applicable_to: list[str] = field(default_factory=list)


@dataclass
class PlanVsActualComparison:
    """Comparison between planned and actual work."""

    planned_goal: str
    actual_goal: str
    planned_approach: str
    actual_approach: str
    planned_outcome: str
    actual_outcome: str
    alignment_score: float


@dataclass
class PostWorkSummary:
    """Comprehensive post-work summary."""

    id: UUID = field(default_factory=uuid4)
    clarity_statement: ClarityStatement = field(default_factory=ClarityStatement)
    plan_vs_actual: PlanVsActualComparison = field(
        default_factory=lambda: PlanVsActualComparison("", "", "", "", "", "", 0.0),
    )
    deviations: list[Deviation] = field(default_factory=list)
    lessons_learned: list[Lesson] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    metrics: ExecutionMetrics = field(default_factory=lambda: ExecutionMetrics(0, 0, 0, 0.0, 0.0))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
