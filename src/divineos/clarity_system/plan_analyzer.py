"""Plan Analyzer.

Parses and normalizes clarity statements into structured plan data.
"""

from typing import Any

from loguru import logger

from .base import PlanAnalyzer
from .types import ClarityStatement, PlanData, PlanMetrics
import sqlite3

_PA_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


class DefaultPlanAnalyzer(PlanAnalyzer):
    """Default implementation of plan analyzer."""

    def __init__(self) -> None:
        """Initialize the plan analyzer."""

    def validate(self) -> bool:
        """Validate component is properly initialized."""
        return True

    def analyze_plan(self, clarity_statement: ClarityStatement) -> PlanData:
        """Analyze clarity statement and extract structured plan.

        Args:
            clarity_statement: Clarity statement to analyze

        Returns:
            Structured plan data

        """
        try:
            goal = self.extract_goal_from_statement(clarity_statement)
            approach = self.extract_approach_from_statement(clarity_statement)
            expected_outcome = clarity_statement.expected_outcome

            # Extract scope metrics
            scope_metrics = self.extract_scope_metrics(clarity_statement)

            plan_metrics = PlanMetrics(
                estimated_files=scope_metrics.get("estimated_files", 0),
                estimated_tool_calls=scope_metrics.get("estimated_tool_calls", 0),
                estimated_complexity=scope_metrics.get("estimated_complexity", "medium"),
                estimated_time_minutes=scope_metrics.get("estimated_time_minutes", 0),
            )

            plan_data = PlanData(
                clarity_statement_id=clarity_statement.id,
                goal=goal,
                approach=approach,
                expected_outcome=expected_outcome,
                metrics=plan_metrics,
            )

            # Normalize the plan data
            plan_data = self.normalize_plan_data(plan_data)

            logger.info(f"Analyzed plan from clarity statement {clarity_statement.id}")
            return plan_data

        except _PA_ERRORS as e:
            logger.error(f"Error analyzing plan: {e}")
            # Return minimal plan data
            return PlanData(
                clarity_statement_id=clarity_statement.id,
                goal=clarity_statement.goal,
                approach=clarity_statement.approach,
                expected_outcome=clarity_statement.expected_outcome,
                metrics=PlanMetrics(0, 0, "medium", 0),
            )

    def extract_goal_from_statement(self, statement: ClarityStatement) -> str:
        """Extract goal from clarity statement.

        Args:
            statement: Clarity statement

        Returns:
            Goal string

        """
        return statement.goal.strip() if statement.goal else "Unspecified goal"

    def extract_approach_from_statement(self, statement: ClarityStatement) -> str:
        """Extract approach from clarity statement.

        Args:
            statement: Clarity statement

        Returns:
            Approach string

        """
        return statement.approach.strip() if statement.approach else "Unspecified approach"

    def extract_scope_metrics(self, clarity_statement: ClarityStatement) -> dict[str, Any]:
        """Extract scope metrics from clarity statement.

        Args:
            clarity_statement: Clarity statement with scope

        Returns:
            Dictionary with scope metrics

        """
        try:
            scope = clarity_statement.scope
            return {
                "estimated_files": scope.estimated_files,
                "estimated_tool_calls": scope.estimated_tool_calls,
                "estimated_complexity": scope.estimated_complexity,
                "estimated_time_minutes": scope.estimated_time_minutes,
            }
        except _PA_ERRORS as e:
            logger.warning(f"Error extracting scope metrics: {e}")
            return {
                "estimated_files": 0,
                "estimated_tool_calls": 0,
                "estimated_complexity": "medium",
                "estimated_time_minutes": 0,
            }

    def normalize_plan_data(self, plan_data: PlanData) -> PlanData:
        """Normalize plan data to standard format.

        Args:
            plan_data: Plan data to normalize

        Returns:
            Normalized plan data

        """
        try:
            # Normalize strings
            goal = plan_data.goal.strip() if plan_data.goal else "Unspecified"
            approach = plan_data.approach.strip() if plan_data.approach else "Unspecified"
            expected_outcome = (
                plan_data.expected_outcome.strip() if plan_data.expected_outcome else "Unspecified"
            )

            # Normalize metrics
            metrics = plan_data.metrics
            if metrics.estimated_complexity not in ["low", "medium", "high"]:
                metrics.estimated_complexity = "medium"

            # Ensure non-negative values
            metrics.estimated_files = max(0, metrics.estimated_files)
            metrics.estimated_tool_calls = max(0, metrics.estimated_tool_calls)
            metrics.estimated_time_minutes = max(0, metrics.estimated_time_minutes)

            normalized_plan = PlanData(
                clarity_statement_id=plan_data.clarity_statement_id,
                goal=goal,
                approach=approach,
                expected_outcome=expected_outcome,
                metrics=metrics,
            )

            logger.info(
                f"Normalized plan data for clarity statement {plan_data.clarity_statement_id}",
            )
            return normalized_plan

        except _PA_ERRORS as e:
            logger.error(f"Error normalizing plan data: {e}")
            return plan_data
