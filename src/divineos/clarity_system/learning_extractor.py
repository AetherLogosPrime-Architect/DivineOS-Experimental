"""Learning Extractor.

Extracts lessons and generates recommendations from deviations and execution data.
"""

from loguru import logger

from .base import LearningExtractor
from .types import Deviation, ExecutionData, Lesson, Recommendation


class DefaultLearningExtractor(LearningExtractor):
    """Default implementation of learning extractor."""

    def __init__(self) -> None:
        """Initialize the learning extractor."""

    def validate(self) -> bool:
        """Validate component is properly initialized."""
        return True

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
        try:
            lessons = []

            # Extract deviation lessons
            deviation_lessons = self.extract_deviation_lessons(deviations)
            lessons.extend(deviation_lessons)

            # Identify tool patterns
            tool_patterns = self.identify_tool_patterns(execution_data)
            lessons.extend(tool_patterns)

            # Identify error patterns
            error_patterns = self._identify_error_patterns(execution_data)
            lessons.extend(error_patterns)

            logger.info(f"Extracted {len(lessons)} lessons from execution")
            return lessons

        except Exception as e:
            logger.error(f"Error extracting lessons: {e}")
            return []

    def extract_deviation_lessons(self, deviations: list[Deviation]) -> list[Lesson]:
        """Extract lessons from deviations.

        Args:
            deviations: List of deviations

        Returns:
            List of lessons

        """
        try:
            lessons: list[Lesson] = []

            # Filter high-severity deviations
            high_severity = [d for d in deviations if d.severity == "high"]

            for deviation in high_severity:
                lesson = Lesson(
                    type="deviation",
                    description=f"High deviation in {deviation.metric}: "
                    f"planned {deviation.planned}, actual {deviation.actual}",
                    context=f"Category: {deviation.category}",
                    insight=self._generate_deviation_insight(deviation),
                    confidence=0.9,
                )
                lessons.append(lesson)

            logger.info(f"Extracted {len(lessons)} deviation lessons")
            return lessons

        except Exception as e:
            logger.error(f"Error extracting deviation lessons: {e}")
            return []

    def identify_tool_patterns(self, execution_data: ExecutionData) -> list[Lesson]:
        """Identify patterns in tool usage.

        Args:
            execution_data: Execution data

        Returns:
            List of lessons about tool patterns

        """
        try:
            lessons: list[Lesson] = []

            if not execution_data.tool_calls:
                return lessons

            # Count tool usage
            tool_counts: dict[str, int] = {}
            for tool_call in execution_data.tool_calls:
                tool_counts[tool_call.tool_name] = tool_counts.get(tool_call.tool_name, 0) + 1

            # Identify most-used tools
            sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)

            if sorted_tools:
                most_used = sorted_tools[0]
                lesson = Lesson(
                    type="pattern",
                    description=f"Most frequently used tool: {most_used[0]} ({most_used[1]} calls)",
                    context="Tool usage pattern",
                    insight=f"Consider optimizing {most_used[0]} usage or batching calls",
                    confidence=0.8,
                )
                lessons.append(lesson)

            logger.info(f"Identified {len(lessons)} tool patterns")
            return lessons

        except Exception as e:
            logger.error(f"Error identifying tool patterns: {e}")
            return []

    def generate_recommendations(self, lessons: list[Lesson]) -> list[Recommendation]:
        """Generate recommendations from lessons.

        Args:
            lessons: List of lessons

        Returns:
            List of recommendations

        """
        try:
            recommendations = []

            for lesson in lessons:
                if lesson.confidence >= 0.7:  # Only recommend high-confidence lessons
                    recommendation = Recommendation(
                        lesson_id=lesson.id,
                        recommendation_text=self._generate_recommendation_text(lesson),
                        priority=self._calculate_priority(lesson),
                        applicable_to=self._identify_applicable_contexts(lesson),
                    )
                    recommendations.append(recommendation)

            logger.info(f"Generated {len(recommendations)} recommendations")
            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    def _identify_error_patterns(self, execution_data: ExecutionData) -> list[Lesson]:
        """Identify patterns in errors.

        Args:
            execution_data: Execution data

        Returns:
            List of lessons about error patterns

        """
        try:
            lessons: list[Lesson] = []

            if not execution_data.errors:
                return lessons

            # Count error types
            error_counts: dict[str, int] = {}
            for error in execution_data.errors:
                # Extract error type (first word or first 50 chars)
                error_type = error.split(":")[0] if ":" in error else error[:50]
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

            # Identify most common errors
            sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)

            if sorted_errors:
                most_common = sorted_errors[0]
                lesson = Lesson(
                    type="error_pattern",
                    description=f"Most common error: {most_common[0]} ({most_common[1]} occurrences)",
                    context="Error pattern",
                    insight=f"Consider addressing root cause of {most_common[0]}",
                    confidence=0.85,
                )
                lessons.append(lesson)

            return lessons

        except Exception as e:
            logger.error(f"Error identifying error patterns: {e}")
            return []

    def _generate_deviation_insight(self, deviation: Deviation) -> str:
        """Generate insight from a deviation."""
        if deviation.difference > 0:
            return f"Actual {deviation.metric} exceeded plan by {deviation.percentage:.1f}%"
        return f"Actual {deviation.metric} was {abs(deviation.percentage):.1f}% less than planned"

    def _generate_recommendation_text(self, lesson: Lesson) -> str:
        """Generate recommendation text from a lesson."""
        if lesson.type == "deviation":
            return f"Review and adjust estimates for {lesson.description}"
        if lesson.type == "pattern":
            return lesson.insight
        if lesson.type == "error_pattern":
            return f"Investigate and fix: {lesson.insight}"
        return f"Consider: {lesson.insight}"

    def _calculate_priority(self, lesson: Lesson) -> str:
        """Calculate priority for a lesson."""
        if lesson.confidence >= 0.9:
            return "high"
        if lesson.confidence >= 0.75:
            return "medium"
        return "low"

    def _identify_applicable_contexts(self, lesson: Lesson) -> list[str]:
        """Identify contexts where lesson is applicable."""
        contexts = []

        if lesson.type == "deviation":
            contexts.append("planning")
            contexts.append("estimation")
        elif lesson.type == "pattern":
            contexts.append("optimization")
            contexts.append("execution")
        elif lesson.type == "error_pattern":
            contexts.append("debugging")
            contexts.append("error_handling")

        return contexts
