"""Abstract base classes for clarity system components.

Defines the interface that each component must implement.
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from .types import (
    ClarityStatement,
    Deviation,
    ExecutionData,
    ExecutionMetrics,
    Lesson,
    PlanData,
    PostWorkSummary,
    Recommendation,
    ScopeEstimate,
)


class ClarityComponent(ABC):
    """Base class for all clarity system components."""

    @abstractmethod
    def validate(self) -> bool:
        """Validate component is properly initialized."""


class ClarityStatementGenerator(ClarityComponent):
    """Generates pre-work clarity statements."""

    @abstractmethod
    def generate_clarity_statement(self, work_context: dict[str, Any]) -> ClarityStatement:
        """Generate a clarity statement from work context.

        Args:
            work_context: Dictionary containing planned work information

        Returns:
            ClarityStatement with goal, approach, outcome, and scope

        """

    @abstractmethod
    def extract_goal(self, work_context: dict[str, Any]) -> str:
        """Extract primary goal from work context."""

    @abstractmethod
    def extract_approach(self, work_context: dict[str, Any]) -> str:
        """Extract approach/strategy from work context."""

    @abstractmethod
    def extract_expected_outcome(self, work_context: dict[str, Any]) -> str:
        """Extract expected outcome from work context."""

    @abstractmethod
    def extract_scope(self, work_context: dict[str, Any]) -> "ScopeEstimate":
        """Extract scope estimate from work context."""

    @abstractmethod
    def present_to_user(self, clarity_statement: ClarityStatement) -> str | None:
        """Present clarity statement to user.

        Args:
            clarity_statement: Statement to present

        Returns:
            Optional user feedback

        """


class PlanAnalyzer(ClarityComponent):
    """Analyzes and normalizes clarity statements into structured plans."""

    @abstractmethod
    def analyze_plan(self, clarity_statement: ClarityStatement) -> PlanData:
        """Analyze clarity statement and extract structured plan.

        Args:
            clarity_statement: Clarity statement to analyze

        Returns:
            Structured plan data

        """

    @abstractmethod
    def extract_goal_from_statement(self, statement: ClarityStatement) -> str:
        """Extract goal from clarity statement."""

    @abstractmethod
    def extract_approach_from_statement(self, statement: ClarityStatement) -> str:
        """Extract approach from clarity statement."""

    @abstractmethod
    def extract_scope_metrics(self, clarity_statement: "ClarityStatement") -> dict[str, Any]:
        """Extract scope metrics from clarity statement."""

    @abstractmethod
    def normalize_plan_data(self, plan_data: PlanData) -> PlanData:
        """Normalize plan data to standard format."""


class ExecutionAnalyzer(ClarityComponent):
    """Queries ledger and extracts actual execution data."""

    @abstractmethod
    def analyze_execution(self, session_id: UUID) -> ExecutionData:
        """Analyze execution from ledger.

        Args:
            session_id: Session ID to analyze

        Returns:
            Structured execution data

        """

    @abstractmethod
    def extract_tool_calls(self, session_id: UUID) -> list[Any]:
        """Extract tool calls from ledger for session."""

    @abstractmethod
    def extract_errors(self, session_id: UUID) -> list[Any]:
        """Extract errors from ledger for session."""

    @abstractmethod
    def calculate_execution_metrics(self, execution_data: ExecutionData) -> ExecutionMetrics:
        """Calculate metrics from execution data."""


class DeviationAnalyzer(ClarityComponent):
    """Compares planned vs actual and identifies deviations."""

    @abstractmethod
    def analyze_deviations(
        self,
        plan_data: PlanData,
        execution_data: ExecutionData,
    ) -> list[Deviation]:
        """Analyze deviations between plan and execution.

        Args:
            plan_data: Planned work data
            execution_data: Actual execution data

        Returns:
            List of deviations

        """

    @abstractmethod
    def compare_metric(self, metric_name: str, planned: float, actual: float) -> Deviation:
        """Compare a single metric and create deviation."""

    @abstractmethod
    def categorize_deviations(self, deviations: list[Deviation]) -> dict[str, list[Deviation]]:
        """Categorize deviations by type."""


class LearningExtractor(ClarityComponent):
    """Extracts lessons and generates recommendations."""

    @abstractmethod
    def extract_lessons(
        self,
        deviations: list[Deviation],
        execution_data: ExecutionData,
    ) -> list[Lesson]:
        """Extract lessons from deviations and execution.

        Args:
            deviations: List of deviations
            execution_data: Execution data

        Returns:
            List of lessons

        """

    @abstractmethod
    def extract_deviation_lessons(self, deviations: list[Deviation]) -> list[Lesson]:
        """Extract lessons from deviations."""

    @abstractmethod
    def identify_tool_patterns(self, execution_data: ExecutionData) -> list[Lesson]:
        """Identify patterns in tool usage."""

    @abstractmethod
    def generate_recommendations(self, lessons: list[Lesson]) -> list[Recommendation]:
        """Generate recommendations from lessons.

        Args:
            lessons: List of lessons

        Returns:
            List of recommendations

        """


class SummaryGenerator(ClarityComponent):
    """Generates comprehensive post-work summaries."""

    @abstractmethod
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

    @abstractmethod
    def generate_plan_vs_actual_section(
        self,
        plan_data: PlanData,
        execution_data: ExecutionData,
    ) -> dict[str, Any]:
        """Generate plan vs actual comparison section."""

    @abstractmethod
    def generate_deviations_section(self, deviations: list[Deviation]) -> dict[str, Any]:
        """Generate deviations section."""

    @abstractmethod
    def generate_metrics_section(self, execution_data: ExecutionData) -> dict[str, Any]:
        """Generate metrics section."""

    @abstractmethod
    def present_summary_to_user(self, summary: PostWorkSummary) -> None:
        """Present summary to user."""
