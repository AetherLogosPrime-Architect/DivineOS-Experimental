"""Abstract base classes for agent integration components.

Defines the interfaces that each component must implement,
ensuring consistent behavior and clear contracts.
"""

from abc import ABC, abstractmethod
from typing import Any

from divineos.agent_integration.types import (
    BehaviorAnalysis,
    SessionFeedback,
    SessionLessons,
    ToolCallEvent,
    ToolResultEvent,
)


class AgentIntegrationComponent(ABC):
    """Base class for all agent integration components."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the component."""

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the component."""


class ToolInterceptor(AgentIntegrationComponent):
    """Abstract base for tool interception and event capture."""

    @abstractmethod
    def intercept_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> ToolCallEvent:
        """Intercept a tool call and emit TOOL_CALL event."""

    @abstractmethod
    def intercept_tool_result(
        self,
        tool_name: str,
        tool_use_id: str,
        result: Any,
        duration_ms: int,
        failed: bool = False,
        error_message: str | None = None,
    ) -> ToolResultEvent:
        """Intercept a tool result and emit TOOL_RESULT event."""


class LoopPrevention(AgentIntegrationComponent):
    """Abstract base for loop prevention."""

    @abstractmethod
    def should_capture_tool(self, tool_name: str) -> bool:
        """Check if tool should be captured."""

    @abstractmethod
    def mark_internal_operation(self) -> None:
        """Context manager to mark operations as internal."""

    @abstractmethod
    def is_internal_operation(self) -> bool:
        """Check if current operation is marked as internal."""


class LearningLoopSystem(AgentIntegrationComponent):
    """Abstract base for learning loop system."""

    @abstractmethod
    def analyze_session_for_lessons(self, session_id: str) -> SessionLessons:
        """Analyze a completed session for lessons."""

    @abstractmethod
    def provide_session_briefing(self, session_id: str) -> dict[str, Any]:
        """Provide briefing of relevant lessons for new session."""


class BehaviorAnalyzer(AgentIntegrationComponent):
    """Abstract base for behavior analysis."""

    @abstractmethod
    def analyze_agent_behavior(self, session_id: str) -> BehaviorAnalysis:
        """Analyze agent behavior for a session."""

    @abstractmethod
    def generate_behavior_report(self, analysis: BehaviorAnalysis) -> str:
        """Generate human-readable behavior report."""


class FeedbackSystem(AgentIntegrationComponent):
    """Abstract base for feedback system."""

    @abstractmethod
    def generate_session_feedback(self, session_id: str) -> SessionFeedback:
        """Generate feedback for a completed session."""

    @abstractmethod
    def store_episode_summary(self, session_id: str, feedback: SessionFeedback) -> str:
        """Store session summary as EPISODE knowledge entry."""
