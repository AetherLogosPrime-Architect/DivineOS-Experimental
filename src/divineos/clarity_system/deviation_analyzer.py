"""Deviation Analyzer.

Compares planned vs actual execution and identifies deviations.
"""

from loguru import logger

from .base import DeviationAnalyzer
from .types import Deviation, ExecutionData, PlanData


class DefaultDeviationAnalyzer(DeviationAnalyzer):
    """Default implementation of deviation analyzer."""

    # Thresholds for deviation severity
    SEVERITY_THRESHOLDS = {
        "low": 0.1,  # 10% deviation
        "medium": 0.25,  # 25% deviation
        "high": 0.5,  # 50% deviation
    }

    def __init__(self) -> None:
        """Initialize the deviation analyzer."""

    def validate(self) -> bool:
        """Validate component is properly initialized."""
        return True

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
        try:
            deviations = []

            # Compare files
            files_deviation = self.compare_metric(
                "files",
                float(plan_data.metrics.estimated_files),
                float(execution_data.metrics.actual_files),
            )
            if files_deviation:
                deviations.append(files_deviation)

            # Compare tool calls
            calls_deviation = self.compare_metric(
                "tool_calls",
                float(plan_data.metrics.estimated_tool_calls),
                float(execution_data.metrics.actual_tool_calls),
            )
            if calls_deviation:
                deviations.append(calls_deviation)

            # Compare time
            time_deviation = self.compare_metric(
                "time",
                float(plan_data.metrics.estimated_time_minutes),
                execution_data.metrics.actual_time_minutes,
            )
            if time_deviation:
                deviations.append(time_deviation)

            # Compare errors (actual errors vs expected 0)
            if execution_data.metrics.actual_errors > 0:
                error_deviation = Deviation(
                    metric="errors",
                    planned=0.0,
                    actual=float(execution_data.metrics.actual_errors),
                    difference=float(execution_data.metrics.actual_errors),
                    percentage=100.0,  # Any error is 100% deviation from plan
                    severity="high",
                    category="quality",
                )
                deviations.append(error_deviation)

            # Categorize deviations
            categorized = self.categorize_deviations(deviations)

            logger.info(
                f"Analyzed deviations: {len(deviations)} total, "
                f"categories: {list(categorized.keys())}",
            )
            return deviations

        except Exception as e:
            logger.error(f"Error analyzing deviations: {e}")
            return []

    def compare_metric(self, metric_name: str, planned: float, actual: float) -> Deviation:
        """Compare a single metric and create deviation.

        Args:
            metric_name: Name of the metric
            planned: Planned value
            actual: Actual value

        Returns:
            Deviation object

        """
        try:
            # Calculate difference
            difference = actual - planned

            # Calculate percentage deviation
            if planned == 0:
                # If planned was 0, any actual value is a deviation
                percentage = 100.0 if actual > 0 else 0.0
            else:
                percentage = abs(difference) / planned * 100.0

            # Determine severity
            severity = self._calculate_severity(percentage)

            # Determine category
            category = self._categorize_metric(metric_name)

            deviation = Deviation(
                metric=metric_name,
                planned=planned,
                actual=actual,
                difference=difference,
                percentage=percentage,
                severity=severity,
                category=category,
            )

            logger.debug(
                f"Compared metric {metric_name}: planned={planned}, actual={actual}, "
                f"deviation={percentage:.1f}%, severity={severity}",
            )
            return deviation

        except Exception as e:
            logger.error(f"Error comparing metric {metric_name}: {e}")
            # Return a zero deviation on error
            return Deviation(
                metric=metric_name,
                planned=planned,
                actual=actual,
                difference=0.0,
                percentage=0.0,
                severity="low",
                category="scope",
            )

    def categorize_deviations(self, deviations: list[Deviation]) -> dict[str, list[Deviation]]:
        """Categorize deviations by type.

        Args:
            deviations: List of deviations

        Returns:
            Dictionary mapping category to list of deviations

        """
        try:
            categorized: dict[str, list[Deviation]] = {
                "scope": [],
                "efficiency": [],
                "quality": [],
                "approach": [],
            }

            for deviation in deviations:
                if deviation.category in categorized:
                    categorized[deviation.category].append(deviation)
                else:
                    # Default to scope if category unknown
                    categorized["scope"].append(deviation)

            logger.info(
                f"Categorized {len(deviations)} deviations: "
                f"{[(k, len(v)) for k, v in categorized.items() if v]}",
            )
            return categorized

        except Exception as e:
            logger.error(f"Error categorizing deviations: {e}")
            return {"scope": [], "efficiency": [], "quality": [], "approach": []}

    def _calculate_severity(self, percentage: float) -> str:
        """Calculate severity level based on percentage deviation.

        Args:
            percentage: Percentage deviation

        Returns:
            Severity level: low, medium, or high

        """
        if percentage <= self.SEVERITY_THRESHOLDS["low"] * 100:
            return "low"
        if percentage <= self.SEVERITY_THRESHOLDS["medium"] * 100:
            return "medium"
        return "high"

    def _categorize_metric(self, metric_name: str) -> str:
        """Categorize a metric by type.

        Args:
            metric_name: Name of the metric

        Returns:
            Category: scope, efficiency, quality, or approach

        """
        if metric_name in ["files", "tool_calls"]:
            return "scope"
        if metric_name == "time":
            return "efficiency"
        if metric_name == "errors":
            return "quality"
        return "approach"
