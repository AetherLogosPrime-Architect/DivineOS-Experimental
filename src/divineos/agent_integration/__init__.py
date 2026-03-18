"""
Kiro Agent Integration Module

Provides automatic event capture for Kiro agent tool calls,
learning loop integration, behavior analysis, and self-improvement feedback.

This module enables the OS to enforce that the Kiro agent uses the system
for all its operations, making self-observation built-in and unavoidable.
"""

from divineos.agent_integration.types import (
    ToolCallEvent,
    ToolResultEvent,
    Correction,
    Encouragement,
    Decision,
    ToolPattern,
    TimingPattern,
    ErrorPattern,
    SessionLessons,
    BehaviorAnalysis,
    SessionFeedback,
    INTERNAL_TOOLS,
)

from divineos.agent_integration.base import (
    AgentIntegrationComponent,
    ToolInterceptor,
    LoopPrevention,
    LearningLoopSystem,
    BehaviorAnalyzer,
    FeedbackSystem,
)

__all__ = [
    # Types
    "ToolCallEvent",
    "ToolResultEvent",
    "Correction",
    "Encouragement",
    "Decision",
    "ToolPattern",
    "TimingPattern",
    "ErrorPattern",
    "SessionLessons",
    "BehaviorAnalysis",
    "SessionFeedback",
    "INTERNAL_TOOLS",
    # Base classes
    "AgentIntegrationComponent",
    "ToolInterceptor",
    "LoopPrevention",
    "LearningLoopSystem",
    "BehaviorAnalyzer",
    "FeedbackSystem",
]
