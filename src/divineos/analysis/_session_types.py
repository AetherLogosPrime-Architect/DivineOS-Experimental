"""Shared dataclasses for session_features and session_features_extra."""

from dataclasses import dataclass


@dataclass
class TaskTracking:
    """Request vs delivery comparison."""

    initial_request: str
    files_changed: int
    user_satisfied: int  # 1=positive, 0=neutral, -1=negative
    summary: str = ""


@dataclass
class ErrorRecoveryEntry:
    """What the AI did after an error."""

    error_timestamp: str
    tool_name: str
    error_summary: str
    recovery_action: str  # retry, investigate, different_approach, ignore
