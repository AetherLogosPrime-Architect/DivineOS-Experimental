"""Event Emission Integration.

Integrates with the existing DivineOS event emission system.
"""

from typing import Any
from uuid import UUID

from loguru import logger

from divineos.core import ledger


class EventEmissionInterface:
    """Interface for emitting clarity-related events."""

    @staticmethod
    def emit_clarity_statement_event(
        session_id: UUID,
        clarity_statement_id: UUID,
        goal: str,
        approach: str,
        expected_outcome: str,
        scope: dict[str, Any],
    ) -> bool:
        """Emit a clarity statement event.

        Args:
            session_id: Session ID
            clarity_statement_id: Clarity statement ID
            goal: Work goal
            approach: Work approach
            expected_outcome: Expected outcome
            scope: Scope estimate

        Returns:
            True if successful, False otherwise

        """
        try:
            payload = {
                "session_id": str(session_id),
                "clarity_statement_id": str(clarity_statement_id),
                "goal": goal,
                "approach": approach,
                "expected_outcome": expected_outcome,
                "scope": scope,
            }

            ledger.log_event(
                event_type="CLARITY_STATEMENT",
                actor="clarity_system",
                payload=payload,
            )

            logger.info(f"Emitted clarity statement event for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error emitting clarity statement event: {e}")
            return False

    @staticmethod
    def emit_summary_event(
        session_id: UUID,
        summary_id: UUID,
        deviations_count: int,
        lessons_count: int,
        recommendations_count: int,
        alignment_score: float,
    ) -> bool:
        """Emit a post-work summary event.

        Args:
            session_id: Session ID
            summary_id: Summary ID
            deviations_count: Number of deviations
            lessons_count: Number of lessons
            recommendations_count: Number of recommendations
            alignment_score: Plan vs actual alignment score

        Returns:
            True if successful, False otherwise

        """
        try:
            payload = {
                "session_id": str(session_id),
                "summary_id": str(summary_id),
                "deviations_count": deviations_count,
                "lessons_count": lessons_count,
                "recommendations_count": recommendations_count,
                "alignment_score": alignment_score,
            }

            ledger.log_event(
                event_type="CLARITY_SUMMARY",
                actor="clarity_system",
                payload=payload,
            )

            logger.info(f"Emitted summary event for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error emitting summary event: {e}")
            return False

    @staticmethod
    def emit_deviation_event(
        session_id: UUID,
        metric: str,
        planned: float,
        actual: float,
        severity: str,
    ) -> bool:
        """Emit a deviation event.

        Args:
            session_id: Session ID
            metric: Metric name
            planned: Planned value
            actual: Actual value
            severity: Deviation severity

        Returns:
            True if successful, False otherwise

        """
        try:
            payload = {
                "session_id": str(session_id),
                "metric": metric,
                "planned": planned,
                "actual": actual,
                "severity": severity,
            }

            ledger.log_event(
                event_type="CLARITY_DEVIATION",
                actor="clarity_system",
                payload=payload,
            )

            logger.debug(f"Emitted deviation event for metric {metric}")
            return True

        except Exception as e:
            logger.error(f"Error emitting deviation event: {e}")
            return False

    @staticmethod
    def emit_lesson_event(
        session_id: UUID,
        lesson_id: UUID,
        lesson_type: str,
        description: str,
        confidence: float,
    ) -> bool:
        """Emit a lesson event.

        Args:
            session_id: Session ID
            lesson_id: Lesson ID
            lesson_type: Type of lesson
            description: Lesson description
            confidence: Confidence score

        Returns:
            True if successful, False otherwise

        """
        try:
            payload = {
                "session_id": str(session_id),
                "lesson_id": str(lesson_id),
                "lesson_type": lesson_type,
                "description": description,
                "confidence": confidence,
            }

            ledger.log_event(
                event_type="CLARITY_LESSON",
                actor="clarity_system",
                payload=payload,
            )

            logger.debug(f"Emitted lesson event: {lesson_type}")
            return True

        except Exception as e:
            logger.error(f"Error emitting lesson event: {e}")
            return False
