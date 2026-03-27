"""Behavior Analyzer for Agent Integration.

Analyzes agent behavior patterns to identify strengths, weaknesses,
and optimization opportunities.
"""

from collections import defaultdict
from typing import Any

from loguru import logger

from divineos.agent_integration.types import BehaviorAnalysis
from divineos.core.error_handling import (
    handle_error,
)
from divineos.core.ledger import get_events


def analyze_agent_behavior(session_id: str) -> BehaviorAnalysis:
    """Analyze agent behavior for a session.

    Args:
        session_id: Session ID to analyze

    Returns:
        BehaviorAnalysis object with all metrics

    """
    logger.info(f"Analyzing agent behavior for session {session_id[:8]}...")

    try:
        # Get all events in session
        events = get_events(limit=10000)
        logger.debug(f"Retrieved {len(events)} events from session")

        # Calculate all metrics
        tool_frequency = calculate_tool_frequency(events)
        success_rates = calculate_success_rates(events)
        execution_times = calculate_execution_times(events)
        error_patterns = analyze_error_patterns(events)
        correction_patterns = analyze_correction_patterns(events)
        decision_patterns = analyze_decision_patterns(events)

        # Create analysis object
        analysis = BehaviorAnalysis(
            session_id=session_id,
            tool_frequency=tool_frequency,
            success_rates=success_rates,
            execution_times=execution_times,
            error_patterns=error_patterns,
            correction_patterns=correction_patterns,
            decision_patterns=decision_patterns,
        )

        logger.info(f"Behavior analysis complete: {len(tool_frequency)} tools analyzed")
        return analysis

    except Exception as e:
        handle_error(e, "analyze_agent_behavior", {"session_id": session_id})
        # Return empty analysis on error
        return BehaviorAnalysis(
            session_id=session_id,
            tool_frequency={},
            success_rates={},
            execution_times={},
            error_patterns={},
            correction_patterns={},
            decision_patterns={},
        )


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


def generate_behavior_report(analysis: BehaviorAnalysis) -> str:
    """Generate human-readable behavior report.

    Args:
        analysis: BehaviorAnalysis object

    Returns:
        Formatted report string

    """
    report_lines = [
        "=== Agent Behavior Report ===",
        f"Session: {analysis.session_id[:8]}...",
        "",
        "Tool Usage:",
    ]

    # Tool frequency
    if analysis.tool_frequency:
        for tool_name, count in sorted(
            analysis.tool_frequency.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            success_rate = analysis.success_rates.get(tool_name, 0)
            report_lines.append(f"  {tool_name}: {count} calls, {success_rate * 100:.1f}% success")
    else:
        report_lines.append("  No tool calls recorded")

    # Timing analysis
    report_lines.append("")
    report_lines.append("Timing Analysis:")
    if analysis.execution_times:
        for tool_name, times in sorted(analysis.execution_times.items()):
            report_lines.append(
                f"  {tool_name}: avg {times['avg_ms']:.0f}ms, "
                f"min {times['min_ms']:.0f}ms, max {times['max_ms']:.0f}ms",
            )
    else:
        report_lines.append("  No timing data available")

    # Error analysis
    report_lines.append("")
    report_lines.append("Error Analysis:")
    if analysis.error_patterns:
        for tool_name, errors in sorted(analysis.error_patterns.items()):
            if errors["error_count"] > 0:
                report_lines.append(
                    f"  {tool_name}: {errors['error_count']} errors, "
                    f"{errors['error_rate'] * 100:.1f}% error rate",
                )
    else:
        report_lines.append("  No errors recorded")

    # Corrections
    report_lines.append("")
    report_lines.append("Corrections (Mistakes Fixed):")
    if analysis.correction_patterns:
        for tool_name, count in sorted(
            analysis.correction_patterns.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            report_lines.append(f"  {tool_name}: {count} corrections")
    else:
        report_lines.append("  No corrections recorded")

    return "\n".join(report_lines)


def identify_optimization_opportunities(analysis: BehaviorAnalysis) -> list[str]:
    """Identify opportunities for optimization.

    Args:
        analysis: BehaviorAnalysis object

    Returns:
        List of optimization recommendations

    """
    opportunities = []

    # Find slow tools
    if analysis.execution_times:
        slow_tools = [
            (tool, times["avg_ms"])
            for tool, times in analysis.execution_times.items()
            if times["avg_ms"] > 500
        ]
        if slow_tools:
            for tool, avg_ms in sorted(slow_tools, key=lambda x: x[1], reverse=True):
                opportunities.append(
                    f"Tool '{tool}' is slow (avg {avg_ms:.0f}ms). Consider optimization.",
                )

    # Find frequently failing tools
    if analysis.error_patterns:
        failing_tools = [
            (tool, errors["error_rate"])
            for tool, errors in analysis.error_patterns.items()
            if errors["error_rate"] > 0.2
        ]
        if failing_tools:
            for tool, error_rate in sorted(failing_tools, key=lambda x: x[1], reverse=True):
                opportunities.append(
                    f"Tool '{tool}' has high error rate ({error_rate * 100:.1f}%). "
                    f"Review error handling.",
                )

    # Find tools with many corrections
    if analysis.correction_patterns:
        corrected_tools = [
            (tool, count) for tool, count in analysis.correction_patterns.items() if count > 2
        ]
        if corrected_tools:
            for tool, count in sorted(corrected_tools, key=lambda x: x[1], reverse=True):
                opportunities.append(
                    f"Tool '{tool}' required {count} corrections. "
                    f"Consider improving error handling or validation.",
                )

    return opportunities


def identify_risky_patterns(analysis: BehaviorAnalysis) -> list[str]:
    """Identify risky patterns to avoid.

    Args:
        analysis: BehaviorAnalysis object

    Returns:
        List of warnings about risky patterns

    """
    warnings = []

    # Find high-error tools
    if analysis.error_patterns:
        high_error_tools = [
            (tool, errors["error_rate"])
            for tool, errors in analysis.error_patterns.items()
            if errors["error_rate"] > 0.5
        ]
        if high_error_tools:
            for tool, error_rate in sorted(high_error_tools, key=lambda x: x[1], reverse=True):
                warnings.append(
                    f"WARNING: Tool '{tool}' has very high error rate ({error_rate * 100:.1f}%). "
                    f"Avoid using this tool without careful validation.",
                )

    return warnings
