"""Agent Integration — self-observation infrastructure for agent sessions.

Provides feedback generation and outcome measurement for the session
pipeline. Originally a larger package; reduced to its used surface
after the 2026-05-03 dead-chain removal (audit Tier 2: deleted
violations_cli, supersession, clarity_enforcement, and the four
internal-cycle modules — decision_store, learning_audit_store,
learning_cycle, pattern_store, pattern_validation — that only had
each other and the deleted clarity_enforcement as callers).

Status: STABLE.

Module map:

  types.py                Dataclasses: ToolCallEvent, Correction,
                          SessionLessons, etc. Used by feedback_system.
  feedback_system.py      Converts analysis into actionable feedback +
                          recommendations. Live entry point from
                          cli/pipeline_phases.py.
  outcome_measurement.py  Measures rework, knowledge drift, correction
                          rates, health. Most-used entry point
                          (analysis_commands, pipeline_phases,
                          progress_dashboard).

Integrates with:
  - core/ledger.py (event storage and retrieval)
  - core/knowledge/ (lesson and feedback storage)
  - analysis/ (session analysis pipeline)
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
