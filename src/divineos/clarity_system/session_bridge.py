"""Session Bridge.

Converts SessionAnalysis data from the session analyzer into clarity system
types so the full clarity pipeline can run on real session data.

Uses the clarity_generator and plan_analyzer modules (previously orphaned)
as the canonical path for creating ClarityStatements and PlanData.
"""

from uuid import uuid4

from .types import (
    ExecutionData,
    ExecutionMetrics,
    ToolCall,
)


def _extract_session_metrics(analysis: object) -> dict:
    """Extract common metrics from a SessionAnalysis object."""
    tool_calls_total = getattr(analysis, "tool_calls_total", 0)
    corrections = getattr(analysis, "corrections", [])
    duration_seconds = getattr(analysis, "duration_seconds", 0.0)
    tool_usage = getattr(analysis, "tool_usage", {})

    file_tools = {"Read", "Write", "Edit", "Glob", "Grep"}
    files_touched = sum(c for t, c in tool_usage.items() if t in file_tools)
    duration_minutes = duration_seconds / 60.0 if duration_seconds else 0.0

    return {
        "tool_calls_total": tool_calls_total,
        "corrections": corrections,
        "duration_minutes": duration_minutes,
        "tool_usage": tool_usage,
        "files_touched": files_touched,
    }


def session_analysis_to_execution_data(analysis: object) -> ExecutionData:
    """Convert a SessionAnalysis into ExecutionData.

    Pulls tool call counts, error counts, and timing from the real session
    analysis that the session_analyzer already computed.
    """
    m = _extract_session_metrics(analysis)

    # Build ToolCall list from tool_usage dict (name -> count)
    tool_call_list = []
    for name, count in m["tool_usage"].items():
        for _ in range(count):
            tool_call_list.append(ToolCall(tool_name=name, timestamp="", input={}))

    # Errors = corrections count (user correcting the agent = something went wrong)
    error_count = len(m["corrections"])

    success_rate = 0.0
    if m["tool_calls_total"] > 0:
        success_rate = max(0.0, (m["tool_calls_total"] - error_count) / m["tool_calls_total"])

    metrics = ExecutionMetrics(
        actual_files=m["files_touched"],
        actual_tool_calls=m["tool_calls_total"],
        actual_errors=error_count,
        actual_time_minutes=m["duration_minutes"],
        success_rate=success_rate,
    )

    return ExecutionData(
        session_id=uuid4(),
        tool_calls=tool_call_list,
        errors=[c.text for c in m["corrections"]] if m["corrections"] else [],
        metrics=metrics,
    )


def synthesize_clarity_statement(analysis: object):
    """Create a ClarityStatement from session analysis using the clarity generator."""
    from .clarity_generator import DefaultClarityStatementGenerator

    m = _extract_session_metrics(analysis)

    generator = DefaultClarityStatementGenerator()
    return generator.generate_clarity_statement(
        {
            "goal": "Session work",
            "approach": "Interactive development",
            "expected_outcome": "Clean execution with no corrections",
            "estimated_files": m["files_touched"],
            "estimated_tool_calls": m["tool_calls_total"],
            "estimated_complexity": "medium",
            "estimated_time_minutes": int(m["duration_minutes"]),
        }
    )


def synthesize_plan_data(analysis: object):
    """Create PlanData from session analysis using the plan analyzer."""
    from .plan_analyzer import DefaultPlanAnalyzer

    clarity_statement = synthesize_clarity_statement(analysis)

    analyzer = DefaultPlanAnalyzer()
    return analyzer.analyze_plan(clarity_statement), clarity_statement


def run_clarity_analysis(analysis: object) -> dict:
    """Run the full clarity pipeline on a SessionAnalysis.

    Chain: clarity_generator -> plan_analyzer -> deviation_analyzer
           -> learning_extractor -> summary_generator -> event_emission

    Returns a dict with the summary and extracted data.
    """
    from .deviation_analyzer import DefaultDeviationAnalyzer
    from .learning_extractor import DefaultLearningExtractor
    from .summary_generator import DefaultSummaryGenerator

    execution_data = session_analysis_to_execution_data(analysis)
    plan_data, clarity_statement = synthesize_plan_data(analysis)

    # 1. Analyze deviations
    deviation_analyzer = DefaultDeviationAnalyzer()
    deviations = deviation_analyzer.analyze_deviations(plan_data, execution_data)

    # 2. Extract lessons from deviations
    learning_extractor = DefaultLearningExtractor()
    lessons = learning_extractor.extract_lessons(deviations, execution_data)
    recommendations = learning_extractor.generate_recommendations(lessons)

    # 3. Generate summary
    summary_generator = DefaultSummaryGenerator()
    summary = summary_generator.generate_post_work_summary(
        clarity_statement=clarity_statement,
        plan_data=plan_data,
        execution_data=execution_data,
        deviations=deviations,
        lessons=lessons,
        recommendations=recommendations,
    )

    # 4. Emit events to ledger for audit trail
    _emit_clarity_events(execution_data.session_id, summary, deviations, lessons)

    return {
        "summary": summary,
        "deviations": deviations,
        "lessons": lessons,
        "recommendations": recommendations,
        "alignment_score": summary.plan_vs_actual.alignment_score,
    }


def _emit_clarity_events(session_id, summary, deviations, lessons):
    """Emit clarity analysis events to the ledger."""
    try:
        from .event_integration import EventEmissionInterface

        # Emit summary event
        EventEmissionInterface.emit_summary_event(
            session_id=session_id,
            summary_id=summary.id,
            deviations_count=len(deviations),
            lessons_count=len(lessons),
            recommendations_count=len(summary.recommendations),
            alignment_score=summary.plan_vs_actual.alignment_score,
        )

        # Emit individual deviation events (high severity only)
        for d in deviations:
            if d.severity == "high":
                EventEmissionInterface.emit_deviation_event(
                    session_id=session_id,
                    metric=d.metric,
                    planned=d.planned,
                    actual=d.actual,
                    severity=d.severity,
                )

        # Emit lesson events
        for lesson in lessons:
            EventEmissionInterface.emit_lesson_event(
                session_id=session_id,
                lesson_id=lesson.id,
                lesson_type=lesson.type,
                description=lesson.description,
                confidence=lesson.confidence,
            )
    except Exception:
        pass  # Event emission is best-effort, never block the pipeline
