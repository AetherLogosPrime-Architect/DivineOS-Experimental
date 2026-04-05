"""Clarity Statement Generator.

Generates pre-work clarity statements that describe planned work to the user.
"""

from typing import Any

from loguru import logger

from .base import ClarityStatementGenerator
from .types import ClarityStatement, ScopeEstimate
import sqlite3

_CG_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


class DefaultClarityStatementGenerator(ClarityStatementGenerator):
    """Default implementation of clarity statement generator."""

    def __init__(self) -> None:
        """Initialize the clarity statement generator."""

    def validate(self) -> bool:
        """Validate component is properly initialized."""
        return True

    def generate_clarity_statement(self, work_context: dict[str, Any]) -> ClarityStatement:
        """Generate a clarity statement from work context.

        Args:
            work_context: Dictionary containing planned work information
                Expected keys: goal, approach, expected_outcome, scope

        Returns:
            ClarityStatement with goal, approach, outcome, and scope

        """
        try:
            goal = self.extract_goal(work_context)
            approach = self.extract_approach(work_context)
            expected_outcome = self.extract_expected_outcome(work_context)
            scope = self.extract_scope(work_context)

            clarity_statement = ClarityStatement(
                goal=goal,
                approach=approach,
                expected_outcome=expected_outcome,
                scope=scope,
            )

            logger.info(
                f"Generated clarity statement {clarity_statement.id} for goal: {goal[:50]}...",
            )
            return clarity_statement

        except _CG_ERRORS as e:
            logger.error(f"Error generating clarity statement: {e}")
            # Return minimal clarity statement with available info
            return ClarityStatement(
                goal=work_context.get("goal", "Unknown goal"),
                approach=work_context.get("approach", "Unknown approach"),
                expected_outcome=work_context.get("expected_outcome", "Unknown outcome"),
                scope=ScopeEstimate(0, 0, "medium", 0),
            )

    def extract_goal(self, work_context: dict[str, Any]) -> str:
        """Extract primary goal from work context.

        Args:
            work_context: Work context dictionary

        Returns:
            Goal string

        """
        if "goal" in work_context:
            goal = work_context["goal"]
            if isinstance(goal, str):
                return goal.strip()
        return "Unspecified goal"

    def extract_approach(self, work_context: dict[str, Any]) -> str:
        """Extract approach/strategy from work context.

        Args:
            work_context: Work context dictionary

        Returns:
            Approach string

        """
        if "approach" in work_context:
            approach = work_context["approach"]
            if isinstance(approach, str):
                return approach.strip()
        return "Unspecified approach"

    def extract_expected_outcome(self, work_context: dict[str, Any]) -> str:
        """Extract expected outcome from work context.

        Args:
            work_context: Work context dictionary

        Returns:
            Expected outcome string

        """
        if "expected_outcome" in work_context:
            outcome = work_context["expected_outcome"]
            if isinstance(outcome, str):
                return outcome.strip()
        return "Unspecified outcome"

    def extract_scope(self, work_context: dict[str, Any]) -> ScopeEstimate:
        """Extract scope estimate from work context.

        Args:
            work_context: Work context dictionary
                Expected keys: estimated_files, estimated_tool_calls,
                              estimated_complexity, estimated_time_minutes

        Returns:
            ScopeEstimate object

        """
        try:
            estimated_files = work_context.get("estimated_files", 0)
            estimated_tool_calls = work_context.get("estimated_tool_calls", 0)
            estimated_complexity = work_context.get("estimated_complexity", "medium")
            estimated_time_minutes = work_context.get("estimated_time_minutes", 0)

            # Validate complexity level
            if estimated_complexity not in ["low", "medium", "high"]:
                estimated_complexity = "medium"

            # Ensure numeric values
            if not isinstance(estimated_files, int):
                estimated_files = 0
            if not isinstance(estimated_tool_calls, int):
                estimated_tool_calls = 0
            if not isinstance(estimated_time_minutes, int):
                estimated_time_minutes = 0

            return ScopeEstimate(
                estimated_files=estimated_files,
                estimated_tool_calls=estimated_tool_calls,
                estimated_complexity=estimated_complexity,
                estimated_time_minutes=estimated_time_minutes,
            )

        except _CG_ERRORS as e:
            logger.warning(f"Error extracting scope: {e}, using defaults")
            return ScopeEstimate(0, 0, "medium", 0)

    def present_to_user(self, clarity_statement: ClarityStatement) -> str | None:
        """Present clarity statement to user.

        Args:
            clarity_statement: Statement to present

        Returns:
            Optional user feedback

        """
        try:
            # Format clarity statement for display
            display_text = self._format_clarity_statement(clarity_statement)
            logger.info(f"Presenting clarity statement to user:\n{display_text}")

            # In a real implementation, this would present to the user
            # and optionally capture feedback. For now, we just log it.
            return None

        except _CG_ERRORS as e:
            logger.error(f"Error presenting clarity statement: {e}")
            return None

    def _format_clarity_statement(self, clarity_statement: ClarityStatement) -> str:
        """Format clarity statement for display.

        Args:
            clarity_statement: Statement to format

        Returns:
            Formatted display string

        """
        lines = [
            "=" * 60,
            "CLARITY STATEMENT (Pre-Work Plan)",
            "=" * 60,
            f"ID: {clarity_statement.id}",
            f"Time: {clarity_statement.timestamp}",
            "",
            "GOAL:",
            f"  {clarity_statement.goal}",
            "",
            "APPROACH:",
            f"  {clarity_statement.approach}",
            "",
            "EXPECTED OUTCOME:",
            f"  {clarity_statement.expected_outcome}",
            "",
            "SCOPE ESTIMATE:",
            f"  Files to modify: {clarity_statement.scope.estimated_files}",
            f"  Tool calls: {clarity_statement.scope.estimated_tool_calls}",
            f"  Complexity: {clarity_statement.scope.estimated_complexity}",
            f"  Time estimate: {clarity_statement.scope.estimated_time_minutes} minutes",
            "",
            "NOTE: This is informational. Work will proceed immediately.",
            "=" * 60,
        ]
        return "\n".join(lines)
