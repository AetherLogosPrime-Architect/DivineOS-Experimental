"""Outcome measurement for the agent learning loop.

This module provides functions to measure various aspects of work outcomes:
- Violations: count CLARITY_VIOLATION events post-work
- Token efficiency: calculate tokens_used / outcome_value
- Hook conflicts: detect hook-related issues
- Rework: detect if issue resurfaces within 5 sessions
"""

from loguru import logger

from divineos.core.ledger import get_events


def measure_violations(
    session_id: str,
    work_start_time: str,
    work_end_time: str,
) -> int:
    """Count CLARITY_VIOLATION events that occurred after work was completed.

    Measures secondary effects of work by counting violations introduced.

    Args:
        session_id: Session ID for the work
        work_start_time: ISO timestamp when work started
        work_end_time: ISO timestamp when work ended

    Returns:
        Count of CLARITY_VIOLATION events post-work
    """
    try:
        # Get all CLARITY_VIOLATION events
        events = get_events(event_type="CLARITY_VIOLATION", limit=10000)

        # Filter to this session and after work end time
        violations = [
            e
            for e in events
            if (
                e.get("payload", {}).get("session_id") == session_id
                and e.get("timestamp", "") > work_end_time
            )
        ]

        logger.info(
            f"Measured {len(violations)} violations for session {session_id} "
            f"after work ended at {work_end_time}"
        )
        return len(violations)
    except Exception as e:
        logger.error(f"Failed to measure violations: {e}")
        return 0


def measure_token_efficiency(
    tokens_used: int,
    outcome_value: float,
) -> float:
    """Calculate token efficiency: tokens_used / outcome_value.

    Measures how efficiently the work used tokens relative to its value.
    Higher efficiency = fewer tokens per unit of value.

    Args:
        tokens_used: Number of tokens consumed
        outcome_value: Value of the outcome (0.0-1.0 scale)

    Returns:
        Token efficiency ratio (tokens per unit value)
    """
    try:
        if outcome_value <= 0:
            logger.warning(f"Invalid outcome_value {outcome_value}, returning 0 efficiency")
            return 0.0

        efficiency = tokens_used / outcome_value
        logger.info(
            f"Measured token efficiency: {tokens_used} tokens / {outcome_value} value "
            f"= {efficiency:.2f} tokens per unit value"
        )
        return efficiency
    except Exception as e:
        logger.error(f"Failed to measure token efficiency: {e}")
        return 0.0


def measure_hook_conflicts(
    session_id: str,
) -> int:
    """Detect hook-related issues in a session.

    Counts events that indicate hook conflicts or issues.

    Args:
        session_id: Session ID to check

    Returns:
        Count of hook-related issues detected
    """
    try:
        # Get all events for this session
        all_events = get_events(limit=10000)

        # Filter to this session
        session_events = [
            e for e in all_events if e.get("payload", {}).get("session_id") == session_id
        ]

        # Count hook-related issues
        # Look for events that indicate hook conflicts
        hook_issues = 0
        for event in session_events:
            payload = event.get("payload", {})
            # Check for hook conflict indicators in payload
            if "hook_conflict" in payload or "hook_error" in payload:
                hook_issues += 1

        logger.info(f"Measured {hook_issues} hook-related issues for session {session_id}")
        return hook_issues
    except Exception as e:
        logger.error(f"Failed to measure hook conflicts: {e}")
        return 0


def measure_rework(
    session_id: str,
    issue_id: str,
    current_session_index: int,
    lookback_sessions: int = 5,
) -> bool:
    """Detect if an issue resurfaces within N sessions.

    Checks if the same issue was worked on in previous sessions,
    indicating that the fix didn't stick (rework needed).

    Args:
        session_id: Current session ID
        issue_id: Issue identifier
        current_session_index: Index of current session
        lookback_sessions: How many previous sessions to check (default 5)

    Returns:
        True if issue resurfaces (rework needed), False otherwise
    """
    try:
        # Get all AGENT_WORK events
        events = get_events(event_type="AGENT_WORK", limit=10000)

        # Find work events for this issue
        issue_work_events = [e for e in events if issue_id in e.get("payload", {}).get("task", "")]

        if not issue_work_events:
            logger.info(f"No previous work found for issue {issue_id}")
            return False

        # Check if issue appears in recent sessions
        # This is a simplified check - in practice would need session indexing
        recent_work = issue_work_events[-lookback_sessions:]

        # If we see the same issue multiple times, it's rework
        rework_detected = len(recent_work) > 1

        logger.info(
            f"Rework detection for issue {issue_id}: "
            f"found {len(recent_work)} work events in last {lookback_sessions} sessions"
        )
        return rework_detected
    except Exception as e:
        logger.error(f"Failed to measure rework: {e}")
        return False
