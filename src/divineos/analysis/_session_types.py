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


@dataclass
class EditReadPairing:
    """One Edit tool call, classified against prior Read tool calls
    on the same file path in the same session.

    ``read_before_edit`` is True iff a Read of ``file_path`` appears
    earlier in the session's tool-call sequence than this Edit.

    False means "no Read of this path observed earlier in the session."
    That is a possible-but-not-certain blind-coding signal: the file
    might have been read in a prior session (persistent knowledge
    the agent legitimately carries). The test still uses it as a
    conservative positive-evidence signal — a session where every
    Edit was preceded by an in-session Read is strong evidence of
    the read-first discipline. The inverse is a weaker signal: some
    Edits without preceding Reads might be legitimate.
    """

    edit_timestamp: str
    file_path: str
    read_before_edit: bool
