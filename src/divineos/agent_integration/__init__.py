"""Agent Integration — self-observation infrastructure for agent sessions.

Captures tool calls as events, extracts lessons from session patterns,
and feeds learning back into future behavior via confidence-weighted
pattern recommendations.

Status: STABLE. Core data flow works end-to-end:
  Tool execution -> event capture -> learning_cycle -> pattern_store -> feedback_system.

Module map (post-2026-04-21 dead-code removal per fresh-Claude audit
round-03952b006724 finding find-445f838344af — 4 modules with zero
production reach were deleted: memory_monitor, memory_actions,
pattern_recommender, learning_loop, plus their test files):

  types.py                Dataclasses: ToolCallEvent, Correction, SessionLessons, etc.
  decision_store.py       Persists AGENT_DECISION events to the ledger. Used by
                          learning_cycle + pattern_validation.
  learning_audit_store.py Stores AGENT_LEARNING_AUDIT events for self-reflection.
                          Used by learning_cycle.
  pattern_store.py        SQLite mutable store for pattern confidence. Used by
                          learning_cycle + pattern_validation.
  learning_cycle.py       Session-end reflection: updates confidence, detects
                          conflicts. Live entry point from
                          clarity_enforcement/violation_logger.py.
  feedback_system.py      Converts analysis into actionable feedback +
                          recommendations. Live entry point from
                          cli/pipeline_phases.py.
  outcome_measurement.py  Measures rework, knowledge drift, correction rates,
                          health. Most-used entry point (analysis_commands,
                          pipeline_phases, progress_dashboard).
  pattern_validation.py   Invalidation, conflict detection, humility audits.
                          Used internally by learning_cycle.

Integrates with:
  - core/ledger.py (event storage and retrieval)
  - core/knowledge/ (lesson and feedback storage)
  - analysis/ (session analysis pipeline)
  - clarity_enforcement/ (violation learning entry point)
"""

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
    "BehaviorAnalysis",
    "Correction",
    "Decision",
    "Encouragement",
    "ErrorPattern",
    "SessionFeedback",
    "SessionLessons",
    "TimingPattern",
    "ToolCallEvent",
    "ToolPattern",
    "ToolResultEvent",
]
