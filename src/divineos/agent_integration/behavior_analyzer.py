"""Behavior Analyzer for Agent Integration.

Analyzes agent behavior patterns to identify strengths, weaknesses,
and optimization opportunities.
"""

from collections import defaultdict
from typing import Any


def calculate_tool_frequency(events: list[dict[str, Any]]) -> dict[str, int]:
    """Calculate tool call frequency.

    Args:
        events: List of events from session

    Returns:
        Dictionary of tool_name -> call_count

    """
    frequency: dict[str, int] = defaultdict(int)

    for event in events:
        if event.get("event_type") == "TOOL_CALL":
            tool_name = event.get("payload", {}).get("tool_name")
            if tool_name:
                frequency[tool_name] += 1

    return dict(frequency)


def calculate_success_rates(events: list[dict[str, Any]]) -> dict[str, float]:
    """Calculate tool success rates.

    Args:
        events: List of events from session

    Returns:
        Dictionary of tool_name -> success_rate (0.0-1.0)

    """
    success_rates = {}
    tool_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "success": 0})

    for event in events:
        if event.get("event_type") == "TOOL_RESULT":
            tool_name = event.get("payload", {}).get("tool_name")
            if tool_name:
                stats = tool_stats[tool_name]
                stats["total"] += 1

                if not event.get("payload", {}).get("failed"):
                    stats["success"] += 1

    for tool_name, stats in tool_stats.items():
        if stats["total"] > 0:
            success_rates[tool_name] = stats["success"] / stats["total"]

    return success_rates


def calculate_execution_times(events: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Calculate tool execution times.

    Args:
        events: List of events from session

    Returns:
        Dictionary of tool_name -> {avg_ms, min_ms, max_ms, median_ms}

    """
    execution_times = {}
    tool_durations = defaultdict(list)

    # Collect durations
    for event in events:
        if event.get("event_type") == "TOOL_RESULT":
            tool_name = event.get("payload", {}).get("tool_name")
            duration = event.get("payload", {}).get("duration_ms", 0)
            if tool_name and duration:
                tool_durations[tool_name].append(duration)

    # Calculate statistics
    for tool_name, durations in tool_durations.items():
        if durations:
            sorted_durations = sorted(durations)
            avg = sum(durations) / len(durations)
            min_d = min(durations)
            max_d = max(durations)
            median = sorted_durations[len(sorted_durations) // 2]

            execution_times[tool_name] = {
                "avg_ms": avg,
                "min_ms": min_d,
                "max_ms": max_d,
                "median_ms": median,
            }

    return execution_times


def analyze_error_patterns(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Analyze error patterns.

    Args:
        events: List of events from session

    Returns:
        Dictionary of tool_name -> {error_count, error_types, error_rate}

    """
    error_patterns = {}
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
                    error_type = error_msg.split()[0] if error_msg else "Unknown"
                    stats["errors"][error_type] += 1

    # Create patterns
    for tool_name, stats in tool_errors.items():
        if stats["total"] > 0:
            error_rate = stats["failed"] / stats["total"]
            error_patterns[tool_name] = {
                "error_count": stats["failed"],
                "error_types": dict(stats["errors"]),
                "error_rate": error_rate,
            }

    return error_patterns


def analyze_correction_patterns(events: list[dict[str, Any]]) -> dict[str, int]:
    """Analyze correction patterns (mistakes made and fixed).

    Args:
        events: List of events from session

    Returns:
        Dictionary of tool_name -> correction_count

    """
    correction_patterns: dict[str, int] = defaultdict(int)
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

            # Look for subsequent successful call to same tool
            for event in events:
                if (
                    event.get("event_type") == "TOOL_RESULT"
                    and not event.get("payload", {}).get("failed")
                    and event.get("payload", {}).get("tool_name") == tool_name
                    and event.get("timestamp", 0) > failure_time
                ):
                    correction_patterns[tool_name] += 1
                    break

    return dict(correction_patterns)


def analyze_decision_patterns(events: list[dict[str, Any]]) -> dict[str, int]:
    """Analyze decision patterns (explicit choices made).

    Args:
        events: List of events from session

    Returns:
        Dictionary of decision_type -> count

    """
    decision_patterns: dict[str, int] = defaultdict(int)

    # Count USER_INPUT events (user decisions)
    for event in events:
        if event.get("event_type") == "USER_INPUT":
            decision_patterns["user_input"] += 1

    # Count EXPLANATION events (agent explanations)
    for event in events:
        if event.get("event_type") == "EXPLANATION":
            decision_patterns["explanation"] += 1

    return dict(decision_patterns)
