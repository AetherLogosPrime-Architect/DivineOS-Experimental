"""Clarity enforcement integration for supersession and contradiction resolution.

This module integrates the supersession system with the clarity enforcement system,
allowing contradictions to be treated as clarity violations.
"""

from typing import Any
from loguru import logger

from divineos.clarity_enforcement.config import ClarityEnforcementMode, get_clarity_config
from divineos.clarity_enforcement.violation_detector import ClarityViolation, ViolationSeverity


def create_contradiction_violation(
    fact1_id: str,
    fact2_id: str,
    fact1_value: Any,
    fact2_value: Any,
    severity: str,
    session_id: str,
) -> ClarityViolation:
    """Create a ClarityViolation for a contradiction.

    Args:
        fact1_id: ID of first fact
        fact2_id: ID of second fact
        fact1_value: Value of first fact
        fact2_value: Value of second fact
        severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW)
        session_id: Session ID

    Returns:
        ClarityViolation object
    """
    # Map contradiction severity to violation severity
    severity_map = {
        "CRITICAL": ViolationSeverity.HIGH,
        "HIGH": ViolationSeverity.HIGH,
        "MEDIUM": ViolationSeverity.MEDIUM,
        "LOW": ViolationSeverity.LOW,
    }

    violation_severity = severity_map.get(severity, ViolationSeverity.MEDIUM)

    return ClarityViolation(
        tool_name="contradiction_detector",
        tool_input={
            "fact1_id": fact1_id,
            "fact2_id": fact2_id,
            "fact1_value": fact1_value,
            "fact2_value": fact2_value,
        },
        severity=violation_severity,
        context=[],
        session_id=session_id,
    )


def handle_unresolved_contradiction(
    fact1_id: str,
    fact2_id: str,
    fact1_value: Any,
    fact2_value: Any,
    severity: str,
    session_id: str,
    is_resolved: bool = False,
) -> None:
    """Handle an unresolved contradiction through clarity enforcement.

    Args:
        fact1_id: ID of first fact
        fact2_id: ID of second fact
        fact1_value: Value of first fact
        fact2_value: Value of second fact
        severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW)
        session_id: Session ID
        is_resolved: Whether the contradiction has been resolved

    Raises:
        ClarityViolationException: If BLOCKING mode and contradiction unresolved
    """
    if is_resolved:
        logger.debug(f"Contradiction between {fact1_id} and {fact2_id} is resolved")
        return

    config = get_clarity_config()

    # Create violation
    violation = create_contradiction_violation(
        fact1_id=fact1_id,
        fact2_id=fact2_id,
        fact1_value=fact1_value,
        fact2_value=fact2_value,
        severity=severity,
        session_id=session_id,
    )

    # Handle based on enforcement mode
    if config.enforcement_mode == ClarityEnforcementMode.BLOCKING:
        _handle_blocking_contradiction(violation, fact1_id, fact2_id, fact1_value, fact2_value)
    elif config.enforcement_mode == ClarityEnforcementMode.LOGGING:
        _handle_logging_contradiction(violation, fact1_id, fact2_id)
    elif config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE:
        _handle_permissive_contradiction(fact1_id, fact2_id)


def _handle_blocking_contradiction(
    violation: ClarityViolation,
    fact1_id: str,
    fact2_id: str,
    fact1_value: Any,
    fact2_value: Any,
) -> None:
    """Handle unresolved contradiction in BLOCKING mode.

    Args:
        violation: The contradiction violation
        fact1_id: ID of first fact
        fact2_id: ID of second fact
        fact1_value: Value of first fact
        fact2_value: Value of second fact

    Raises:
        ClarityViolationException: Always raised to block execution
    """
    from divineos.clarity_enforcement.enforcer import ClarityViolationException

    logger.error(f"BLOCKING mode: Unresolved contradiction between {fact1_id} and {fact2_id}")

    # Raise exception
    raise ClarityViolationException(
        violation,
        f"BLOCKING mode: Unresolved contradiction between {fact1_id} "
        f"({fact1_value}) and {fact2_id} ({fact2_value}). "
        f"Please resolve this contradiction.",
    )


def _handle_logging_contradiction(
    violation: ClarityViolation,
    fact1_id: str,
    fact2_id: str,
) -> None:
    """Handle unresolved contradiction in LOGGING mode.

    Args:
        violation: The contradiction violation
        fact1_id: ID of first fact
        fact2_id: ID of second fact
    """
    logger.warning(f"LOGGING mode: Unresolved contradiction between {fact1_id} and {fact2_id}")


def _handle_permissive_contradiction(
    fact1_id: str,
    fact2_id: str,
) -> None:
    """Handle unresolved contradiction in PERMISSIVE mode.

    Args:
        fact1_id: ID of first fact
        fact2_id: ID of second fact
    """
    logger.debug(
        f"PERMISSIVE mode: Allowing unresolved contradiction between {fact1_id} and {fact2_id}"
    )
