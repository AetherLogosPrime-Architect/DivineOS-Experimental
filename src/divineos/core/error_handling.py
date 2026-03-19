"""Error Handling Infrastructure for DivineOS.

This module provides a centralized exception hierarchy and error handling utilities.
All DivineOS exceptions inherit from DivineOSError, ensuring consistent error handling.

Usage:
    from divineos.core.error_handling import (
        DivineOSError,
        EventCaptureError,
        LedgerError,
        SessionError,
        ToolExecutionError,
        handle_error,
    )
    from loguru import logger

    try:
        # Some operation
        pass
    except EventCaptureError as e:
        handle_error(e, "event_capture_operation")
"""

from typing import Any

from loguru import logger


class DivineOSError(Exception):
    """Base exception for all DivineOS errors.

    All DivineOS-specific exceptions inherit from this class, allowing
    callers to catch all DivineOS errors with a single except clause.
    """


class EventCaptureError(DivineOSError):
    """Exception raised when event capture fails.

    This error occurs when the system cannot capture an event due to
    validation failures, storage issues, or other event-related problems.
    """


class LedgerError(DivineOSError):
    """Exception raised when ledger operations fail.

    This error occurs when the system cannot read from or write to the
    ledger (SQLite database), including validation and integrity issues.
    """


class SessionError(DivineOSError):
    """Exception raised when session management fails.

    This error occurs when the system cannot create, retrieve, or manage
    session state, including session_id generation and persistence.
    """


class ToolExecutionError(DivineOSError):
    """Exception raised when tool execution fails.

    This error occurs when a wrapped tool fails to execute, including
    parameter validation, execution errors, and result capture failures.
    """


def handle_error(
    error: Exception,
    context: str,
    extra_info: dict[str, Any] | None = None,
) -> None:
    """Log an error with context and stack trace.

    This function ensures all errors are logged with full context before
    being handled or propagated. It includes the stack trace to aid debugging.

    Args:
        error: The exception to log
        context: A string describing where the error occurred (e.g., "event_capture")
        extra_info: Optional dictionary of additional context information

    Example:
        try:
            capture_event(event)
        except EventCaptureError as e:
            handle_error(e, "event_capture", {"event_id": event.id})
            # Decide whether to propagate or handle

    """
    extra_context = extra_info or {}
    logger.error(
        f"Error in {context}: {error}",
        exc_info=True,
        extra={"context": context, **extra_context},
    )
