"""Agent Integration — self-observation infrastructure for agent sessions.

Captures tool calls as events, extracts lessons from session patterns,
and feeds learning back into future behavior via confidence-weighted
pattern recommendations.

Status: STABLE. Core data flow works end-to-end:
  Tool execution → event capture → learning loop → pattern store → recommendations.

Module map (14 files):
  base.py              Abstract contracts: ToolInterceptor, LearningLoopSystem, etc.
  types.py             Dataclasses: ToolCallEvent, Correction, SessionLessons, etc.
  decision_store.py    Persists AGENT_DECISION events to the ledger.
  learning_audit_store.py  Stores AGENT_LEARNING_AUDIT events for self-reflection.
  pattern_store.py     SQLite mutable store for pattern confidence (not ledger).
  learning_loop.py     Extracts corrections, encouragements, decisions from sessions.
  learning_cycle.py    Session-end reflection: updates confidence, detects conflicts.
  feedback_system.py   Converts analysis into actionable feedback + recommendations.
  outcome_measurement.py  Measures rework, knowledge drift, correction rates, health.
  memory_monitor.py    Token budget tracking and automatic context compression.
  memory_actions.py    Singleton access and convenience functions.
  pattern_recommender.py  Context-aware pattern matching and humility warnings.
  pattern_validation.py   Invalidation, conflict detection, humility audits.

Integrates with:
  - core/ledger.py (event storage and retrieval)
  - core/knowledge/ (lesson and feedback storage)
  - analysis/ (session analysis pipeline)
  - core/hud.py (engagement and briefing display)
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
