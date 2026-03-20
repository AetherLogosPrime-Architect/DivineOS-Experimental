"""Violation logging system for clarity enforcement.

Emits CLARITY_VIOLATION events and logs violations to system log.
"""

from loguru import logger
from .violation_detector import ClarityViolation
from .config import ClarityEnforcementMode
from divineos.event.event_emission import emit_clarity_violation


class ViolationLogger:
    """Logs clarity violations."""

    def log_violation(
        self,
        violation: ClarityViolation,
        enforcement_mode: ClarityEnforcementMode,
        action_taken: str,
    ) -> None:
        """Log a clarity violation.

        Args:
            violation: The violation to log
            enforcement_mode: Current enforcement mode
            action_taken: Action taken in response to violation
        """
        # Log to system log
        logger.warning(
            f"Clarity violation: {violation.tool_name} "
            f"({violation.severity.value} severity) - {action_taken}"
        )

        # Log full context
        logger.debug(f"Violation details: {violation.to_dict()}")
        logger.debug(f"Enforcement mode: {enforcement_mode.value}")

    def emit_clarity_violation_event(
        self,
        violation: ClarityViolation,
        enforcement_mode: ClarityEnforcementMode,
        action_taken: str,
    ) -> str:
        """Emit a CLARITY_VIOLATION event to the ledger.

        Args:
            violation: The violation to emit
            enforcement_mode: Current enforcement mode
            action_taken: Action taken in response to violation

        Returns:
            event_id: The ID of the stored event
        """
        # Emit event to ledger
        event_id = emit_clarity_violation(
            tool_name=violation.tool_name,
            tool_input=violation.tool_input,
            violation_severity=violation.severity.value,
            enforcement_mode=enforcement_mode.value,
            action_taken=action_taken,
            context=violation.context,
            session_id=violation.session_id,
            user_role=violation.user_role,
            agent_name=violation.agent_name,
        )

        logger.debug(f"Emitted CLARITY_VIOLATION event: {event_id}")
        return event_id


def emit_clarity_violation_event(
    violation: ClarityViolation,
    enforcement_mode: ClarityEnforcementMode,
    action_taken: str,
) -> str:
    """Emit a CLARITY_VIOLATION event to the ledger.

    Args:
        violation: The violation to emit
        enforcement_mode: Current enforcement mode
        action_taken: Action taken in response to violation

    Returns:
        event_id: The ID of the stored event
    """
    logger_instance = ViolationLogger()
    return logger_instance.emit_clarity_violation_event(violation, enforcement_mode, action_taken)


def log_clarity_violation(
    violation: ClarityViolation,
    enforcement_mode: ClarityEnforcementMode,
    action_taken: str,
) -> None:
    """Log a clarity violation to the system log.

    Args:
        violation: The violation to log
        enforcement_mode: Current enforcement mode
        action_taken: Action taken in response to violation
    """
    logger_instance = ViolationLogger()
    logger_instance.log_violation(violation, enforcement_mode, action_taken)
