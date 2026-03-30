"""Error recovery implementations for each integration point."""

from typing import Any, Optional
import sqlite3
from loguru import logger

from divineos.integration.error_handler import (
    RetryableError,
    retry_on_error,
)

_ER_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


class ClarityEnforcementRecovery:
    """Error recovery for Clarity Enforcement → Learning Loop integration."""

    @staticmethod
    @retry_on_error(max_retries=3)
    def capture_violation_with_recovery(
        learning_cycle: Any,
        violation_event: dict[str, Any],
    ) -> bool:
        """Capture violation with error recovery.

        Args:
            learning_cycle: LearningCycle instance
            violation_event: Violation event to capture

        Returns:
            True if successful, False otherwise
        """
        try:
            learning_cycle.capture_violation_event(violation_event)
            logger.info(f"Violation captured: {violation_event.get('tool_name')}")
            return True
        except _ER_ERRORS as e:
            logger.error(f"Failed to capture violation: {e}")
            raise RetryableError(f"Violation capture failed: {e}")


class ContradictionResolutionRecovery:
    """Error recovery for Contradiction Detection → Resolution Engine integration."""

    @staticmethod
    @retry_on_error(max_retries=3)
    def resolve_contradiction_with_recovery(
        engine: Any,
        detector: Any,
        fact1: dict[str, Any],
        fact2: dict[str, Any],
    ) -> Optional[Any]:
        """Resolve contradiction with error recovery.

        Args:
            engine: ResolutionEngine instance
            detector: ContradictionDetector instance
            fact1: First fact
            fact2: Second fact

        Returns:
            SupersessionEvent or None
        """
        try:
            engine.register_fact(fact1)
            engine.register_fact(fact2)

            contradiction = detector.detect_contradiction(fact1, fact2)
            if not contradiction:
                logger.warning("No contradiction detected")
                return None

            from divineos.supersession import ResolutionStrategy

            supersession = engine.resolve_contradiction(
                contradiction, ResolutionStrategy.NEWER_FACT
            )
            logger.info(f"Contradiction resolved: {supersession.event_id}")
            return supersession
        except _ER_ERRORS as e:
            logger.error(f"Failed to resolve contradiction: {e}")
            raise RetryableError(f"Contradiction resolution failed: {e}")


class MemoryMonitorRecovery:
    """Error recovery for Memory Monitor → Learning Cycle integration."""

    @staticmethod
    @retry_on_error(max_retries=2)
    def save_checkpoint_with_recovery(
        monitor: Any,
        task: str,
        status: str,
        files_modified: list[str],
        tests_passing: int,
    ) -> bool:
        """Save checkpoint with error recovery.

        Args:
            monitor: MemoryMonitor instance
            task: Task name
            status: Task status
            files_modified: List of modified files
            tests_passing: Number of passing tests

        Returns:
            True if successful
        """
        try:
            monitor.save_work_checkpoint(
                task=task,
                status=status,
                files_modified=files_modified,
                tests_passing=tests_passing,
            )
            logger.info(f"Checkpoint saved: {task}")
            return True
        except _ER_ERRORS as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise RetryableError(f"Checkpoint save failed: {e}")

    @staticmethod
    @retry_on_error(max_retries=2)
    def update_token_usage_with_recovery(
        monitor: Any,
        tokens: int,
    ) -> bool:
        """Update token usage with error recovery.

        Args:
            monitor: MemoryMonitor instance
            tokens: Number of tokens used

        Returns:
            True if successful
        """
        try:
            monitor.update_token_usage(tokens)
            logger.info(f"Token usage updated: {tokens}")
            return True
        except _ER_ERRORS as e:
            logger.error(f"Failed to update token usage: {e}")
            raise RetryableError(f"Token update failed: {e}")


class LedgerStorageRecovery:
    """Error recovery for Tool Execution → Ledger Storage integration."""

    @staticmethod
    @retry_on_error(max_retries=3)
    def log_event_with_recovery(
        event_type: str,
        actor: str,
        payload: dict[str, Any],
    ) -> Optional[str]:
        """Log event with error recovery.

        Args:
            event_type: Type of event
            actor: Actor performing the action
            payload: Event payload

        Returns:
            Event ID or None
        """
        try:
            from divineos.core.ledger import log_event

            event_id = log_event(
                event_type=event_type,
                actor=actor,
                payload=payload,
                validate=False,
            )
            logger.info(f"Event logged: {event_type} ({event_id})")
            return event_id
        except _ER_ERRORS as e:
            logger.error(f"Failed to log event: {e}")
            raise RetryableError(f"Event logging failed: {e}")


class QueryInterfaceRecovery:
    """Error recovery for Query Interface → Current Fact Resolution integration."""

    @staticmethod
    @retry_on_error(max_retries=2)
    def get_current_fact_with_recovery(
        engine: Any,
        fact_type: str,
        fact_key: str,
    ) -> Optional[dict[str, Any]]:
        """Get current fact with error recovery.

        Args:
            engine: ResolutionEngine instance
            fact_type: Type of fact
            fact_key: Key of fact

        Returns:
            Current fact or None
        """
        try:
            current: Optional[dict[str, Any]] = engine.get_current_truth(fact_type, fact_key)
            if current:
                logger.info(f"Current fact retrieved: {current.get('id')}")
            else:
                logger.warning(f"No current fact found: {fact_type}/{fact_key}")
            return current
        except _ER_ERRORS as e:
            logger.error(f"Failed to get current fact: {e}")
            raise RetryableError(f"Query failed: {e}")

    @staticmethod
    @retry_on_error(max_retries=2)
    def get_supersession_chain_with_recovery(
        engine: Any,
        fact_id: str,
    ) -> Optional[list[Any]]:
        """Get supersession chain with error recovery.

        Args:
            engine: ResolutionEngine instance
            fact_id: ID of fact

        Returns:
            Supersession chain or None
        """
        try:
            chain: Optional[list[Any]] = engine.get_supersession_chain(fact_id)
            logger.info(f"Supersession chain retrieved: {len(chain) if chain else 0} events")
            return chain
        except _ER_ERRORS as e:
            logger.error(f"Failed to get supersession chain: {e}")
            raise RetryableError(f"Chain retrieval failed: {e}")
