"""Learning Loop System for Agent Integration.

Extracts lessons from agent operations and stores them as knowledge entries
for self-improvement and behavior analysis.
"""

from collections import defaultdict
from typing import Any
import sqlite3

from loguru import logger

from divineos.agent_integration.types import (
    Correction,
    Decision,
    Encouragement,
    ErrorPattern,
    SessionLessons,
    TimingPattern,
    ToolPattern,
)
from divineos.core.error_handling import (
    handle_error,
)
from divineos.core.ledger import get_events
from divineos.event.event_capture import get_current_timestamp

_LL_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


def analyze_session_for_lessons(session_id: str) -> SessionLessons:
    """Analyze a completed session for lessons.

    Args:
        session_id: Session ID to analyze

    Returns:
        SessionLessons object containing all extracted lessons

    """
    logger.info(f"Analyzing session {session_id[:8]}... for lessons")

    try:
        # Get all events in session
        events = get_events(limit=10000)
        logger.debug(f"Retrieved {len(events)} events from session")

        # Create lessons object
        lessons = SessionLessons(session_id=session_id)

        # Extract different types of lessons
        lessons.corrections = extract_corrections(events)
        logger.debug(f"Extracted {len(lessons.corrections)} corrections")

        lessons.encouragements = extract_encouragements(events)
        logger.debug(f"Extracted {len(lessons.encouragements)} encouragements")

        lessons.decisions = extract_decisions(events)
        logger.debug(f"Extracted {len(lessons.decisions)} decisions")

        lessons.tool_patterns = extract_tool_patterns(events)
        logger.debug(f"Extracted {len(lessons.tool_patterns)} tool patterns")

        lessons.timing_patterns = extract_timing_patterns(events)
        logger.debug(f"Extracted {len(lessons.timing_patterns)} timing patterns")

        lessons.error_patterns = extract_error_patterns(events)
        logger.debug(f"Extracted {len(lessons.error_patterns)} error patterns")

        logger.info(
            f"Session analysis complete: {len(lessons.corrections)} corrections, "
            f"{len(lessons.encouragements)} encouragements, "
            f"{len(lessons.decisions)} decisions",
        )

        return lessons

    except _LL_ERRORS as e:
        handle_error(e, "analyze_session_for_lessons", {"session_id": session_id})
        # Return empty lessons on error
        return SessionLessons(session_id=session_id)


def extract_corrections(events: list[dict[str, Any]]) -> list[Correction]:
    """Extract corrections (mistakes made and fixed).

    Args:
        events: List of events from session

    Returns:
        List of Correction objects

    """
    corrections = []
    failed_tools = defaultdict(list)

    # Find failed tool calls
    for event in events:
        if event.get("event_type") == "TOOL_RESULT" and event.get("payload", {}).get("failed"):
            tool_name = event.get("payload", {}).get("tool_name")
            if tool_name:
                failed_tools[tool_name].append(event)

    # Find subsequent successful attempts
    for tool_name, failures in failed_tools.items():
        for failure in failures:
            failure_time = failure.get("timestamp", 0)
            error_msg = failure.get("payload", {}).get("error_message", "Unknown error")

            # Look for subsequent successful call to same tool
            for event in events:
                if (
                    event.get("event_type") == "TOOL_RESULT"
                    and not event.get("payload", {}).get("failed")
                    and event.get("payload", {}).get("tool_name") == tool_name
                    and event.get("timestamp", 0) > failure_time
                ):
                    correction = Correction(
                        tool_name=tool_name,
                        error_message=error_msg,
                        fixed=True,
                        session_id=failure.get("payload", {}).get("session_id", ""),
                        timestamp=get_current_timestamp(),
                    )
                    corrections.append(correction)
                    break

    return corrections


def extract_encouragements(events: list[dict[str, Any]]) -> list[Encouragement]:
    """Extract encouragements (successful patterns).

    Args:
        events: List of events from session

    Returns:
        List of Encouragement objects

    """
    encouragements = []
    successful_tools: dict[str, int] = defaultdict(int)

    # Track successful tool calls
    for event in events:
        if event.get("event_type") == "TOOL_RESULT" and not event.get("payload", {}).get("failed"):
            tool_name = event.get("payload", {}).get("tool_name")
            if tool_name:
                successful_tools[tool_name] += 1

    # Create encouragements for frequently successful tools
    for tool_name, success_count in successful_tools.items():
        if success_count >= 2:  # At least 2 successful calls
            encouragement = Encouragement(
                description=f"Successfully used {tool_name} {success_count} times",
                tool_names=[tool_name],
                success_count=success_count,
                session_id="",
                timestamp=get_current_timestamp(),
            )
            encouragements.append(encouragement)

    return encouragements


def extract_decisions(events: list[dict[str, Any]]) -> list[Decision]:
    """Extract decisions (explicit choices made).

    Args:
        events: List of events from session

    Returns:
        List of Decision objects

    """
    decisions = []

    # Extract from USER_INPUT events (user decisions)
    for event in events:
        if event.get("event_type") == "USER_INPUT":
            content = event.get("payload", {}).get("content", "")
            if content and len(content) > 10:  # Meaningful input
                decision = Decision(
                    description=content[:200],
                    context="User input",
                    outcome="Processed",
                    session_id=event.get("payload", {}).get("session_id", ""),
                    timestamp=get_current_timestamp(),
                )
                decisions.append(decision)

    return decisions


def extract_tool_patterns(events: list[dict[str, Any]]) -> dict[str, ToolPattern]:
    """Extract tool usage patterns.

    Args:
        events: List of events from session

    Returns:
        Dictionary of tool_name -> ToolPattern

    """
    patterns = {}
    tool_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "successes": 0, "failures": 0, "durations": []},
    )

    # Collect statistics
    for event in events:
        if event.get("event_type") == "TOOL_RESULT":
            tool_name = event.get("payload", {}).get("tool_name")
            if tool_name:
                stats = tool_stats[tool_name]
                stats["calls"] += 1

                if event.get("payload", {}).get("failed"):
                    stats["failures"] += 1
                else:
                    stats["successes"] += 1

                duration = event.get("payload", {}).get("duration_ms", 0)
                if duration:
                    stats["durations"].append(duration)

    # Create patterns
    for tool_name, stats in tool_stats.items():
        if stats["calls"] > 0:
            success_rate = stats["successes"] / stats["calls"]
            avg_duration = (
                sum(stats["durations"]) / len(stats["durations"]) if stats["durations"] else 0
            )
            min_duration = min(stats["durations"]) if stats["durations"] else 0
            max_duration = max(stats["durations"]) if stats["durations"] else 0

            pattern = ToolPattern(
                tool_name=tool_name,
                call_count=stats["calls"],
                success_count=stats["successes"],
                failure_count=stats["failures"],
                success_rate=success_rate,
                avg_duration_ms=avg_duration,
                min_duration_ms=min_duration,
                max_duration_ms=max_duration,
            )
            patterns[tool_name] = pattern

    return patterns


def extract_timing_patterns(events: list[dict[str, Any]]) -> dict[str, TimingPattern]:
    """Extract timing patterns for tools.

    Args:
        events: List of events from session

    Returns:
        Dictionary of tool_name -> TimingPattern

    """
    patterns = {}
    tool_durations = defaultdict(list)

    # Collect durations
    for event in events:
        if event.get("event_type") == "TOOL_RESULT":
            tool_name = event.get("payload", {}).get("tool_name")
            duration = event.get("payload", {}).get("duration_ms", 0)
            if tool_name and duration:
                tool_durations[tool_name].append(duration)

    # Create patterns
    for tool_name, durations in tool_durations.items():
        if durations:
            sorted_durations = sorted(durations)
            avg = sum(durations) / len(durations)
            min_d = min(durations)
            max_d = max(durations)
            median = sorted_durations[len(sorted_durations) // 2]
            p95 = (
                sorted_durations[int(len(sorted_durations) * 0.95)]
                if len(sorted_durations) > 1
                else max_d
            )
            p99 = (
                sorted_durations[int(len(sorted_durations) * 0.99)]
                if len(sorted_durations) > 1
                else max_d
            )

            pattern = TimingPattern(
                tool_name=tool_name,
                avg_duration_ms=avg,
                min_duration_ms=min_d,
                max_duration_ms=max_d,
                median_duration_ms=median,
                p95_duration_ms=p95,
                p99_duration_ms=p99,
            )
            patterns[tool_name] = pattern

    return patterns


def extract_error_patterns(events: list[dict[str, Any]]) -> dict[str, ErrorPattern]:
    """Extract error patterns for tools.

    Args:
        events: List of events from session

    Returns:
        Dictionary of tool_name -> ErrorPattern

    """
    patterns = {}
    tool_errors: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "errors": defaultdict(int), "failed": 0},
    )

    # Collect errors
    for event in events:
        if event.get("event_type") == "TOOL_RESULT":
            tool_name = event.get("payload", {}).get("tool_name")
            if tool_name:
                stats = tool_errors[tool_name]
                stats["total"] += 1

                if event.get("payload", {}).get("failed"):
                    stats["failed"] += 1
                    error_msg = event.get("payload", {}).get("error_message", "Unknown")
                    # Extract error type (first word or first 50 chars)
                    error_type = error_msg.split()[0] if error_msg else "Unknown"
                    stats["errors"][error_type] += 1

    # Create patterns
    for tool_name, stats in tool_errors.items():
        if stats["total"] > 0:
            error_rate = stats["failed"] / stats["total"]
            most_common = (
                max(stats["errors"].items(), key=lambda x: x[1])[0] if stats["errors"] else "None"
            )

            pattern = ErrorPattern(
                tool_name=tool_name,
                error_count=stats["failed"],
                error_types=dict(stats["errors"]),
                most_common_error=most_common,
                error_rate=error_rate,
            )
            patterns[tool_name] = pattern

    return patterns
