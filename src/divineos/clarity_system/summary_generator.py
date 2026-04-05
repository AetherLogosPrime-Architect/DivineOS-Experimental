"""Summary Generator.

Generates comprehensive post-work summaries with analysis and recommendations.
"""

from typing import Any

from loguru import logger

from .base import SummaryGenerator
from .types import (
    ClarityStatement,
    Deviation,
    ExecutionData,
    Lesson,
    PlanData,
    PlanVsActualComparison,
    PostWorkSummary,
    Recommendation,
)
import sqlite3

_SG_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


class DefaultSummaryGenerator(SummaryGenerator):
    """Default implementation of summary generator."""

    def __init__(self) -> None:
        """Initialize the summary generator."""

    def validate(self) -> bool:
        """Validate component is properly initialized."""
        return True

    def generate_post_work_summary(
        self,
        clarity_statement: ClarityStatement,
        plan_data: PlanData,
        execution_data: ExecutionData,
        deviations: list[Deviation],
        lessons: list[Lesson],
        recommendations: list[Recommendation],
    ) -> PostWorkSummary:
        """Generate comprehensive post-work summary.

        Args:
            clarity_statement: Original clarity statement
            plan_data: Planned work data
            execution_data: Actual execution data
            deviations: Identified deviations
            lessons: Extracted lessons
            recommendations: Generated recommendations

        Returns:
            Comprehensive post-work summary

        """
        try:
            # Generate plan vs actual comparison
            plan_vs_actual_section = self.generate_plan_vs_actual_section(plan_data, execution_data)
            plan_vs_actual = PlanVsActualComparison(
                planned_goal=plan_vs_actual_section.get("planned_goal", ""),
                actual_goal=plan_vs_actual_section.get("actual_goal", ""),
                planned_approach=plan_vs_actual_section.get("planned_approach", ""),
                actual_approach=plan_vs_actual_section.get("actual_approach", ""),
                planned_outcome=plan_vs_actual_section.get("planned_outcome", ""),
                actual_outcome=plan_vs_actual_section.get("actual_outcome", ""),
                alignment_score=plan_vs_actual_section.get("alignment_score", 0.0),
            )

            # Create summary
            summary = PostWorkSummary(
                clarity_statement=clarity_statement,
                plan_vs_actual=plan_vs_actual,
                deviations=deviations,
                lessons_learned=lessons,
                recommendations=recommendations,
                metrics=execution_data.metrics,
            )

            logger.info(
                f"Generated post-work summary {summary.id}: "
                f"{len(deviations)} deviations, {len(lessons)} lessons, "
                f"{len(recommendations)} recommendations",
            )
            return summary

        except _SG_ERRORS as e:
            logger.error(f"Error generating post-work summary: {e}")
            # Return minimal summary
            return PostWorkSummary(
                clarity_statement=clarity_statement,
                plan_vs_actual=PlanVsActualComparison("", "", "", "", "", "", 0.0),
                deviations=[],
                lessons_learned=[],
                recommendations=[],
                metrics=execution_data.metrics,
            )

    def generate_plan_vs_actual_section(
        self,
        plan_data: PlanData,
        execution_data: ExecutionData,
    ) -> dict[str, Any]:
        """Generate plan vs actual comparison section.

        Args:
            plan_data: Planned work data
            execution_data: Actual execution data

        Returns:
            Dictionary with comparison data

        """
        try:
            # Calculate alignment score (0-100)
            alignment_score = self._calculate_alignment_score(plan_data, execution_data)

            section = {
                "planned_goal": plan_data.goal,
                "actual_goal": plan_data.goal,  # Goal typically doesn't change
                "planned_approach": plan_data.approach,
                "actual_approach": plan_data.approach,  # Approach typically doesn't change
                "planned_outcome": plan_data.expected_outcome,
                "actual_outcome": plan_data.expected_outcome,
                "alignment_score": alignment_score,
                "metrics_comparison": {
                    "files": {
                        "planned": plan_data.metrics.estimated_files,
                        "actual": execution_data.metrics.actual_files,
                    },
                    "tool_calls": {
                        "planned": plan_data.metrics.estimated_tool_calls,
                        "actual": execution_data.metrics.actual_tool_calls,
                    },
                    "time_minutes": {
                        "planned": plan_data.metrics.estimated_time_minutes,
                        "actual": execution_data.metrics.actual_time_minutes,
                    },
                },
            }

            logger.debug(f"Generated plan vs actual section with alignment {alignment_score:.1f}%")
            return section

        except _SG_ERRORS as e:
            logger.error(f"Error generating plan vs actual section: {e}")
            return {}

    def generate_deviations_section(self, deviations: list[Deviation]) -> dict[str, Any]:
        """Generate deviations section.

        Args:
            deviations: List of deviations

        Returns:
            Dictionary with deviations data

        """
        try:
            # Categorize deviations
            by_severity: dict[str, list[Deviation]] = {"high": [], "medium": [], "low": []}
            by_category: dict[str, list[Deviation]] = {}

            for deviation in deviations:
                by_severity[deviation.severity].append(deviation)
                if deviation.category not in by_category:
                    by_category[deviation.category] = []
                by_category[deviation.category].append(deviation)

            section = {
                "total_deviations": len(deviations),
                "by_severity": {k: len(v) for k, v in by_severity.items()},
                "by_category": {k: len(v) for k, v in by_category.items()},
                "high_severity_deviations": [
                    {
                        "metric": d.metric,
                        "planned": d.planned,
                        "actual": d.actual,
                        "percentage": d.percentage,
                    }
                    for d in by_severity["high"]
                ],
            }

            logger.debug(f"Generated deviations section with {len(deviations)} deviations")
            return section

        except _SG_ERRORS as e:
            logger.error(f"Error generating deviations section: {e}")
            return {}

    def generate_metrics_section(self, execution_data: ExecutionData) -> dict[str, Any]:
        """Generate metrics section.

        Args:
            execution_data: Execution data

        Returns:
            Dictionary with metrics data

        """
        try:
            metrics = execution_data.metrics

            section = {
                "files_accessed": metrics.actual_files,
                "tool_calls": metrics.actual_tool_calls,
                "errors": metrics.actual_errors,
                "time_minutes": metrics.actual_time_minutes,
                "success_rate": f"{metrics.success_rate:.1%}",
            }

            logger.debug("Generated metrics section")
            return section

        except _SG_ERRORS as e:
            logger.error(f"Error generating metrics section: {e}")
            return {}

    def present_summary_to_user(self, summary: PostWorkSummary) -> None:
        """Present summary to user.

        Args:
            summary: Summary to present

        """
        try:
            display_text = self._format_summary(summary)
            logger.info(f"Presenting post-work summary to user:\n{display_text}")

            # In a real implementation, this would present to the user
            # For now, we just log it

        except _SG_ERRORS as e:
            logger.error(f"Error presenting summary: {e}")

    def _calculate_alignment_score(
        self,
        plan_data: PlanData,
        execution_data: ExecutionData,
    ) -> float:
        """Calculate alignment score between plan and execution.

        Args:
            plan_data: Planned work data
            execution_data: Actual execution data

        Returns:
            Alignment score (0-100)

        """
        try:
            scores = []

            # Score files alignment
            if plan_data.metrics.estimated_files > 0:
                files_ratio = min(
                    execution_data.metrics.actual_files / plan_data.metrics.estimated_files,
                    1.0,
                )
                scores.append(files_ratio * 100)
            else:
                scores.append(100.0)

            # Score tool calls alignment
            if plan_data.metrics.estimated_tool_calls > 0:
                calls_ratio = min(
                    execution_data.metrics.actual_tool_calls
                    / plan_data.metrics.estimated_tool_calls,
                    1.0,
                )
                scores.append(calls_ratio * 100)
            else:
                scores.append(100.0)

            # Score error rate (lower is better)
            error_score = max(0, 100 - (execution_data.metrics.actual_errors * 10))
            scores.append(error_score)

            # Average all scores
            return sum(scores) / len(scores) if scores else 0.0

        except _SG_ERRORS as e:
            logger.error(f"Error calculating alignment score: {e}")
            return 0.0

    def _format_summary(self, summary: PostWorkSummary) -> str:
        """Format summary for display.

        Args:
            summary: Summary to format

        Returns:
            Formatted display string

        """
        lines = [
            "=" * 60,
            "POST-WORK SUMMARY",
            "=" * 60,
            f"ID: {summary.id}",
            f"Time: {summary.timestamp}",
            "",
            "ORIGINAL CLARITY STATEMENT:",
            f"  Goal: {summary.clarity_statement.goal}",
            f"  Approach: {summary.clarity_statement.approach}",
            "",
            "EXECUTION METRICS:",
            f"  Files accessed: {summary.metrics.actual_files}",
            f"  Tool calls: {summary.metrics.actual_tool_calls}",
            f"  Errors: {summary.metrics.actual_errors}",
            f"  Time: {summary.metrics.actual_time_minutes:.1f} minutes",
            f"  Success rate: {summary.metrics.success_rate:.1%}",
            "",
            "DEVIATIONS:",
            f"  Total: {len(summary.deviations)}",
        ]

        if summary.deviations:
            high_severity = [d for d in summary.deviations if d.severity == "high"]
            if high_severity:
                lines.append(f"  High severity: {len(high_severity)}")
                for d in high_severity[:3]:  # Show top 3
                    lines.append(f"    - {d.metric}: {d.percentage:.1f}% deviation")

        lines.extend(
            [
                "",
                "LESSONS LEARNED:",
                f"  Total: {len(summary.lessons_learned)}",
            ],
        )

        if summary.lessons_learned:
            for lesson in summary.lessons_learned[:3]:  # Show top 3
                lines.append(f"    - {lesson.type}: {lesson.description[:50]}...")

        lines.extend(
            [
                "",
                "RECOMMENDATIONS:",
                f"  Total: {len(summary.recommendations)}",
            ],
        )

        if summary.recommendations:
            for rec in summary.recommendations[:3]:  # Show top 3
                lines.append(f"    - [{rec.priority}] {rec.recommendation_text[:50]}...")

        lines.append("=" * 60)
        return "\n".join(lines)
