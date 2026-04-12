"""Enforcement system for clarity requirements.

Enforces clarity requirements based on configuration (BLOCKING, LOGGING, PERMISSIVE).
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from .config import ClarityConfig, ClarityEnforcementMode, get_clarity_config
from .violation_detector import ClarityViolation, detect_clarity_violation
from .violation_logger import emit_clarity_violation_event, log_clarity_violation


class ClarityViolationException(Exception):
    """Raised when a clarity violation is detected in BLOCKING mode."""

    def __init__(self, violation: ClarityViolation, message: str = ""):
        self.violation = violation
        self.message = message or f"Clarity violation: {violation.tool_name} is unexplained"
        super().__init__(self.message)


class ClarityEnforcer:
    """Enforces clarity requirements."""

    def __init__(self, config: Optional[ClarityConfig] = None):
        """Initialize enforcer with configuration.

        Args:
            config: ClarityConfig instance. If None, loads from environment/defaults.
        """
        self.config = config or get_clarity_config()
        logger.debug(f"ClarityEnforcer initialized with mode: {self.config.enforcement_mode.value}")

    def enforce(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: List[str],
        session_id: str,
    ) -> None:
        """Enforce clarity requirements for a tool call.

        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters for the tool
            context: Preceding messages (conversation context)
            session_id: Current session ID

        Raises:
            ClarityViolationException: If BLOCKING mode and violation detected
        """
        # Detect violations
        violation = detect_clarity_violation(tool_name, tool_input, context, session_id)

        if violation is None:
            # No violation, tool call is explained
            logger.debug(f"Tool call {tool_name} is explained, no enforcement action needed")
            return

        # Handle violation based on enforcement mode
        if self.config.enforcement_mode == ClarityEnforcementMode.BLOCKING:
            self._handle_blocking_violation(violation)
        elif self.config.enforcement_mode == ClarityEnforcementMode.LOGGING:
            self._handle_logging_violation(violation)
        elif self.config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE:
            self._handle_permissive_violation(violation)

    def _handle_blocking_violation(self, violation: ClarityViolation) -> None:
        """Handle violation in BLOCKING mode.

        Args:
            violation: The violation detected

        Raises:
            ClarityViolationException: Always raised to block execution
        """
        logger.error(f"BLOCKING mode: Preventing unexplained tool call {violation.tool_name}")

        # Log the violation
        log_clarity_violation(
            violation,
            ClarityEnforcementMode.BLOCKING,
            "blocked",
        )

        # Emit event
        if self.config.emit_events:
            emit_clarity_violation_event(
                violation,
                ClarityEnforcementMode.BLOCKING,
                "blocked",
            )

        # Raise exception to prevent execution
        raise ClarityViolationException(
            violation,
            f"BLOCKING mode: Tool call {violation.tool_name} lacks explanation. "
            f"Please provide a clear explanation of why this tool is being called.",
        )

    def _handle_logging_violation(self, violation: ClarityViolation) -> None:
        """Handle violation in LOGGING mode.

        Args:
            violation: The violation detected
        """
        logger.warning(f"LOGGING mode: Logging unexplained tool call {violation.tool_name}")

        # Log the violation
        log_clarity_violation(
            violation,
            ClarityEnforcementMode.LOGGING,
            "logged",
        )

        # Emit event
        if self.config.emit_events:
            emit_clarity_violation_event(
                violation,
                ClarityEnforcementMode.LOGGING,
                "logged",
            )

    def _handle_permissive_violation(self, violation: ClarityViolation) -> None:
        """Handle violation in PERMISSIVE mode.

        Args:
            violation: The violation detected
        """
        logger.debug(f"PERMISSIVE mode: Allowing unexplained tool call {violation.tool_name}")
        # No action taken in PERMISSIVE mode


def enforce_clarity(
    tool_name: str,
    tool_input: Dict[str, Any],
    context: List[str],
    session_id: str,
    config: Optional[ClarityConfig] = None,
) -> None:
    """Enforce clarity requirements for a tool call.

    Args:
        tool_name: Name of the tool being called
        tool_input: Input parameters for the tool
        context: Preceding messages (conversation context)
        session_id: Current session ID
        config: ClarityConfig instance. If None, loads from environment/defaults.

    Raises:
        ClarityViolationException: If BLOCKING mode and violation detected
    """
    enforcer = ClarityEnforcer(config)
    enforcer.enforce(tool_name, tool_input, context, session_id)
