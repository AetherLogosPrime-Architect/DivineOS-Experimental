"""Kiro Agent Integration Module.

Provides automatic event capture for Kiro agent tool calls,
learning loop integration, behavior analysis, and self-improvement feedback.

This module enables the OS to enforce that the Kiro agent uses the system
for all its operations, making self-observation built-in and unavoidable.
"""

from divineos.agent_integration.base import (
    AgentIntegrationComponent,
    BehaviorAnalyzer,
    FeedbackSystem,
    LearningLoopSystem,
    LoopPrevention,
    ToolInterceptor,
)
from divineos.agent_integration.types import (
    INTERNAL_TOOLS,
    BehaviorAnalysis,
    Correction,
    Decision,
    Encouragement,
    ErrorPattern,
    SessionFeedback,
    SessionLessons,
    TimingPattern,
    ToolCallEvent,
    ToolPattern,
    ToolResultEvent,
)

__all__ = [
    "INTERNAL_TOOLS",
    # Base classes
    "AgentIntegrationComponent",
    "BehaviorAnalysis",
    "BehaviorAnalyzer",
    "Correction",
    "Decision",
    "Encouragement",
    "ErrorPattern",
    "FeedbackSystem",
    "LearningLoopSystem",
    "LoopPrevention",
    "SessionFeedback",
    "SessionLessons",
    "TimingPattern",
    # Types
    "ToolCallEvent",
    "ToolInterceptor",
    "ToolPattern",
    "ToolResultEvent",
]
