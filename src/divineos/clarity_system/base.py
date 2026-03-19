"""
Abstract base classes for clarity system components.

Defines the interface that each component must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from uuid import UUID

from .types import (
    ClarityStatement,
    PlanData,
    ExecutionData,
    ExecutionMetrics,
    Deviation,
    Lesson,
    Recommendation,
    PostWorkSummary,
    ScopeEstimate,
)


class ClarityComponent(ABC):
    """Base class for all clarity system components."""

    @abstractmethod
    def validate(self) -> bool:
        """Validate component is properly initialized."""
        pass


class ClarityStatementGenerator(ClarityComponent):
    """Generates pre-work clarity statements."""

    @abstractmethod
    def generate_clarity_statement(self, work_context: Dict[str, Any]) -> ClarityStatement:
        """
        Generate a clarity statement from work context.

        Args:
            work_context: Dictionary containing planned work information

        Returns:
            ClarityStatement with goal, approach, outcome, and scope
        """
        pass

    @abstractmethod
    def extract_goal(self, work_context: Dict[str, Any]) -> str:
        """Extract primary goal from work context."""
        pass

    @abstractmethod
    def extract_approach(self, work_context: Dict[str, Any]) -> str:
        """Extract approach/strategy from work context."""
        pass

    @abstractmethod
    def extract_expected_outcome(self, work_context: Dict[str, Any]) -> str:
        """Extract expected outcome from work context."""
        pass

    @abstractmethod
    def extract_scope(self, work_context: Dict[str, Any]) -> "ScopeEstimate":
        """Extract scope estimate from work context."""
        pass

    @abstractmethod
    def present_to_user(self, clarity_statement: ClarityStatement) -> Optional[str]:
        """
        Present clarity statement to user.

        Args:
            clarity_statement: Statement to present

        Returns:
            Optional user feedback
        """
        pass


class PlanAnalyzer(ClarityComponent):
    """Analyzes and normalizes clarity statements into structured plans."""

    @abstractmethod
    def analyze_plan(self, clarity_statement: ClarityStatement) -> PlanData:
        """
        Analyze clarity statement and extract structured plan.

        Args:
            clarity_statement: Clarity statement to analyze

        Returns:
            Structured plan data
        """
        pass

    @abstractmethod
    def extract_goal_from_statement(self, statement: ClarityStatement) -> str:
        """Extract goal from clarity statement."""
        pass

    @abstractmethod
    def extract_approach_from_statement(self, statement: ClarityStatement) -> str:
        """Extract approach from clarity statement."""
        pass

    @abstractmethod
    def extract_scope_metrics(self, clarity_statement: "ClarityStatement") -> Dict[str, Any]:
        """Extract scope metrics from clarity statement."""
        pass

    @abstractmethod
    def normalize_plan_data(self, plan_data: PlanData) -> PlanData:
        """Normalize plan data to standard format."""
        pass


class ExecutionAnalyzer(ClarityComponent):
    """Queries ledger and extracts actual execution data."""

    @abstractmethod
    def analyze_execution(self, session_id: UUID) -> ExecutionData:
        """
        Analyze execution from ledger.

        Args:
            session_id: Session ID to analyze

        Returns:
            Structured execution data
        """
        pass

    @abstractmethod
    def extract_tool_calls(self, session_id: UUID) -> list:
        """Extract tool calls from ledger for session."""
        pass

    @abstractmethod
    def extract_errors(self, session_id: UUID) -> list:
        """Extract errors from ledger for session."""
        pass

    @abstractmethod
    def calculate_execution_metrics(self, execution_data: ExecutionData) -> ExecutionMetrics:
        """Calculate metrics from execution data."""
        pass


class DeviationAnalyzer(ClarityComponent):
    """Compares planned vs actual and identifies deviations."""

    @abstractmethod
    def analyze_deviations(
        self, plan_data: PlanData, execution_data: ExecutionData
    ) -> list[Deviation]:
        """
        Analyze deviations between plan and execution.

        Args:
            plan_data: Planned work data
            execution_data: Actual execution data

        Returns:
            List of deviations
        """
        pass

    @abstractmethod
    def compare_metric(self, metric_name: str, planned: float, actual: float) -> Deviation:
        """Compare a single metric and create deviation."""
        pass

    @abstractmethod
    def categorize_deviations(self, deviations: list[Deviation]) -> Dict[str, list[Deviation]]:
        """Categorize deviations by type."""
        pass


class LearningExtractor(ClarityComponent):
    """Extracts lessons and generates recommendations."""

    @abstractmethod
    def extract_lessons(
        self, deviations: list[Deviation], execution_data: ExecutionData
    ) -> list[Lesson]:
        """
        Extract lessons from deviations and execution.

        Args:
            deviations: List of deviations
            execution_data: Execution data

        Returns:
            List of lessons
        """
        pass

    @abstractmethod
    def extract_deviation_lessons(self, deviations: list[Deviation]) -> list[Lesson]:
        """Extract lessons from deviations."""
        pass

    @abstractmethod
    def identify_tool_patterns(self, execution_data: ExecutionData) -> list[Lesson]:
        """Identify patterns in tool usage."""
        pass

    @abstractmethod
    def generate_recommendations(self, lessons: list[Lesson]) -> list[Recommendation]:
        """
        Generate recommendations from lessons.

        Args:
            lessons: List of lessons

        Returns:
            List of recommendations
        """
        pass


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
        """
        Generate comprehensive post-work summary.

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
        pass

    @abstractmethod
    def generate_plan_vs_actual_section(
        self, plan_data: PlanData, execution_data: ExecutionData
    ) -> Dict[str, Any]:
        """Generate plan vs actual comparison section."""
        pass

    @abstractmethod
    def generate_deviations_section(self, deviations: list[Deviation]) -> Dict[str, Any]:
        """Generate deviations section."""
        pass

    @abstractmethod
    def generate_metrics_section(self, execution_data: ExecutionData) -> Dict[str, Any]:
        """Generate metrics section."""
        pass

    @abstractmethod
    def present_summary_to_user(self, summary: PostWorkSummary) -> None:
        """Present summary to user."""
        pass
