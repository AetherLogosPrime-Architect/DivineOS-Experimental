"""Feedback System for Agent Integration.

Generates comprehensive feedback on agent operations to support self-improvement.
"""

from datetime import datetime, timezone
from typing import Any

from loguru import logger

from divineos.agent_integration.behavior_analyzer import analyze_agent_behavior
from divineos.agent_integration.learning_loop import analyze_session_for_lessons
from divineos.agent_integration.types import SessionFeedback
from divineos.core.consolidation import store_knowledge
from divineos.core.error_handling import (
    handle_error,
)


def get_iso8601_timestamp() -> str:
    """Get current timestamp in ISO8601 format."""
    return datetime.now(timezone.utc).isoformat()


def generate_session_feedback(session_id: str) -> SessionFeedback:
    """Generate feedback for a completed session.

    Args:
        session_id: Session ID to analyze

    Returns:
        SessionFeedback object with comprehensive feedback

    """
    logger.info(f"Generating session feedback for {session_id[:8]}...")

    try:
        # Get behavior analysis
        analysis = analyze_agent_behavior(session_id)
        logger.debug("Behavior analysis complete")

        # Get lessons learned
        lessons = analyze_session_for_lessons(session_id)
        logger.debug("Lesson analysis complete")

        # Generate recommendations
        recommendations = generate_recommendations(analysis, lessons)
        logger.debug(f"Generated {len(recommendations)} recommendations")

        # Get historical patterns (for now, empty)
        historical: dict[str, Any] = {}
        comparison = compare_to_historical_patterns(analysis, historical)
        logger.debug("Historical comparison complete")

        # Create feedback object
        feedback = SessionFeedback(
            session_id=session_id,
            tool_usage=analysis.tool_frequency,
            success_rates=analysis.success_rates,
            timing=analysis.execution_times,
            errors=[
                f"{tool}: {errors['error_count']} errors ({errors['error_rate'] * 100:.1f}%)"
                for tool, errors in analysis.error_patterns.items()
            ],
            lessons_learned=[
                f"{len(lessons.corrections)} corrections, "
                f"{len(lessons.encouragements)} encouragements, "
                f"{len(lessons.decisions)} decisions",
            ],
            recommendations=recommendations,
            improvements=comparison.get("improvements", []),
            regressions=comparison.get("regressions", []),
        )

        logger.info(f"Session feedback generated: {len(recommendations)} recommendations")
        return feedback

    except Exception as e:
        handle_error(e, "generate_session_feedback", {"session_id": session_id})
        # Return empty feedback on error
        return SessionFeedback(
            session_id=session_id,
            tool_usage={},
            success_rates={},
            timing={},
            errors=[],
            lessons_learned=[],
            recommendations=[],
            improvements=[],
            regressions=[],
        )


def generate_session_summary(
    session_id: str,
    analysis: Any,
    lessons: Any,
    recommendations: list[str],
) -> dict[str, Any]:
    """Generate comprehensive session summary.

    Args:
        session_id: Session ID
        analysis: BehaviorAnalysis object
        lessons: SessionLessons object
        recommendations: List of recommendations

    Returns:
        Dictionary with session summary

    """
    return {
        "session_id": session_id,
        "tool_usage": analysis.tool_frequency,
        "success_rates": analysis.success_rates,
        "timing": analysis.execution_times,
        "errors": analysis.error_patterns,
        "lessons_learned": {
            "corrections": len(lessons.corrections),
            "encouragements": len(lessons.encouragements),
            "decisions": len(lessons.decisions),
        },
        "recommendations": recommendations,
        "timestamp": get_iso8601_timestamp(),
    }


def compare_to_historical_patterns(
    current_analysis: Any,  # pylint: disable=unused-argument
    historical_data: dict[str, Any],  # pylint: disable=unused-argument
) -> dict[str, Any]:
    """Compare current session to historical patterns.

    Args:
        current_analysis: BehaviorAnalysis object for current session
        historical_data: Historical data (empty for now)

    Returns:
        Dictionary with comparison results

    """
    # For now, return empty comparison
    # This will be enhanced when historical data is available
    return {
        "improvements": [],
        "regressions": [],
        "comparison": {},
    }


def generate_recommendations(analysis: Any, lessons: Any) -> list[str]:
    """Generate specific, actionable recommendations.

    Args:
        analysis: BehaviorAnalysis object
        lessons: SessionLessons object

    Returns:
        List of recommendations

    """
    recommendations = []

    # Recommendations based on success rates
    if analysis.success_rates:
        low_success_tools = [
            (tool, rate) for tool, rate in analysis.success_rates.items() if rate < 0.8
        ]
        if low_success_tools:
            for tool, rate in sorted(low_success_tools, key=lambda x: x[1]):
                recommendations.append(
                    f"Tool '{tool}' has {rate * 100:.1f}% success rate. "
                    f"Consider improving error handling or validation.",
                )

    # Recommendations based on timing
    if analysis.execution_times:
        slow_tools = [
            (tool, times["avg_ms"])
            for tool, times in analysis.execution_times.items()
            if times["avg_ms"] > 1000
        ]
        if slow_tools:
            for tool, avg_ms in sorted(slow_tools, key=lambda x: x[1], reverse=True):
                recommendations.append(
                    f"Tool '{tool}' takes {avg_ms:.0f}ms on average. "
                    f"Consider optimizing or caching results.",
                )

    # Recommendations based on corrections
    if analysis.correction_patterns:
        corrected_tools = [
            (tool, count) for tool, count in analysis.correction_patterns.items() if count > 1
        ]
        if corrected_tools:
            for tool, count in sorted(corrected_tools, key=lambda x: x[1], reverse=True):
                recommendations.append(
                    f"Tool '{tool}' required {count} corrections. "
                    f"Review error handling and add better validation.",
                )

    # Recommendations based on lessons
    if lessons.encouragements:
        recommendations.append(
            f"Great job! You successfully used {len(lessons.encouragements)} tools "
            f"with consistent success. Keep up this pattern.",
        )

    if lessons.corrections:
        recommendations.append(
            f"You made {len(lessons.corrections)} mistakes but fixed them. "
            f"This shows good error recovery. Document these fixes for future reference.",
        )

    # Add general recommendations
    if not recommendations:
        recommendations.append("Session completed successfully. No specific improvements needed.")

    return recommendations


def store_episode_summary(session_id: str, feedback: SessionFeedback) -> str:
    """Store session summary as EPISODE knowledge entry.

    Args:
        session_id: Session ID
        feedback: SessionFeedback object

    Returns:
        Knowledge entry ID

    """
    logger.info(f"Storing episode summary for session {session_id[:8]}...")

    try:
        entry_id = store_knowledge(
            knowledge_type="EPISODE",
            content=str(feedback.to_dict()),
            confidence=1.0,
            source_events=[session_id],
            tags=["agent-learning", "session-summary"],
        )
        logger.debug(f"Stored episode summary: {entry_id[:8]}...")
        return entry_id
    except Exception as e:
        handle_error(e, "store_episode_summary", {"session_id": session_id})
        raise


def format_feedback_report(feedback: SessionFeedback) -> str:
    """Format feedback as a human-readable report.

    Args:
        feedback: SessionFeedback object

    Returns:
        Formatted report string

    """
    report_lines = [
        "=== Session Feedback Report ===",
        f"Session: {feedback.session_id[:8]}...",
        "",
        "Tool Usage:",
    ]

    # Tool usage
    if feedback.tool_usage:
        for tool, count in sorted(feedback.tool_usage.items(), key=lambda x: x[1], reverse=True):
            success_rate = feedback.success_rates.get(tool, 0)
            report_lines.append(f"  {tool}: {count} calls, {success_rate * 100:.1f}% success")
    else:
        report_lines.append("  No tool calls recorded")

    # Timing
    report_lines.append("")
    report_lines.append("Timing Analysis:")
    if feedback.timing:
        for tool, times in sorted(feedback.timing.items()):
            report_lines.append(f"  {tool}: avg {times['avg_ms']:.0f}ms")
    else:
        report_lines.append("  No timing data available")

    # Errors
    report_lines.append("")
    report_lines.append("Errors:")
    if feedback.errors:
        for error in feedback.errors:
            report_lines.append(f"  {error}")
    else:
        report_lines.append("  No errors recorded")

    # Lessons
    report_lines.append("")
    report_lines.append("Lessons Learned:")
    if feedback.lessons_learned:
        for lesson in feedback.lessons_learned:
            report_lines.append(f"  {lesson}")
    else:
        report_lines.append("  No lessons recorded")

    # Recommendations
    report_lines.append("")
    report_lines.append("Recommendations:")
    if feedback.recommendations:
        for i, rec in enumerate(feedback.recommendations, 1):
            report_lines.append(f"  {i}. {rec}")
    else:
        report_lines.append("  No recommendations")

    # Improvements/Regressions
    if feedback.improvements or feedback.regressions:
        report_lines.append("")
        if feedback.improvements:
            report_lines.append("Improvements:")
            for imp in feedback.improvements:
                report_lines.append(f"  [+] {imp}")
        if feedback.regressions:
            report_lines.append("Regressions:")
            for reg in feedback.regressions:
                report_lines.append(f"  [-] {reg}")

    return "\n".join(report_lines)
