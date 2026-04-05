"""Hooks for violation events and custom handlers."""

from typing import Callable, Optional, List, Dict
from enum import Enum
import logging
import sqlite3

from divineos.clarity_enforcement.violation_detector import ClarityViolation

_HOOKS_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


logger = logging.getLogger(__name__)


class ViolationEventType(Enum):
    """Types of violation events."""

    DETECTED = "on_violation_detected"
    LOGGED = "on_violation_logged"
    BLOCKED = "on_violation_blocked"
    RESOLVED = "on_violation_resolved"


class ViolationHook:
    """Hook for violation events."""

    def __init__(
        self,
        event_type: ViolationEventType,
        handler: Callable[[ClarityViolation], None],
        name: Optional[str] = None,
    ):
        """
        Initialize violation hook.

        Args:
            event_type: Type of violation event
            handler: Callback function to handle event
            name: Optional name for the hook
        """
        self.event_type = event_type
        self.handler = handler
        self.name = name or f"{event_type.value}_{id(handler)}"

    def trigger(self, violation: ClarityViolation) -> None:
        """
        Trigger the hook with a violation.

        Args:
            violation: Violation that triggered the hook
        """
        try:
            self.handler(violation)
        except _HOOKS_ERRORS as e:
            logger.error(
                f"Error in hook {self.name}: {e}",
                exc_info=True,
            )


class ViolationHookRegistry:
    """Registry for violation hooks."""

    def __init__(self):
        """Initialize hook registry."""
        self._hooks: Dict[ViolationEventType, List[ViolationHook]] = {
            event_type: [] for event_type in ViolationEventType
        }

    def register(
        self,
        event_type: ViolationEventType,
        handler: Callable[[ClarityViolation], None],
        name: Optional[str] = None,
    ) -> ViolationHook:
        """
        Register a violation hook.

        Args:
            event_type: Type of violation event
            handler: Callback function
            name: Optional name for the hook

        Returns:
            Registered hook
        """
        hook = ViolationHook(event_type, handler, name)
        self._hooks[event_type].append(hook)
        logger.debug(f"Registered hook: {hook.name}")
        return hook

    def unregister(
        self,
        event_type: ViolationEventType,
        hook_name: str,
    ) -> bool:
        """
        Unregister a violation hook.

        Args:
            event_type: Type of violation event
            hook_name: Name of hook to unregister

        Returns:
            True if hook was unregistered
        """
        hooks = self._hooks[event_type]
        for i, hook in enumerate(hooks):
            if hook.name == hook_name:
                hooks.pop(i)
                logger.debug(f"Unregistered hook: {hook_name}")
                return True
        return False

    def trigger(
        self,
        event_type: ViolationEventType,
        violation: ClarityViolation,
    ) -> None:
        """
        Trigger all hooks for an event type.

        Args:
            event_type: Type of violation event
            violation: Violation that triggered the event
        """
        hooks = self._hooks.get(event_type, [])
        for hook in hooks:
            hook.trigger(violation)

    def get_hooks(
        self,
        event_type: ViolationEventType,
    ) -> List[ViolationHook]:
        """
        Get all hooks for an event type.

        Args:
            event_type: Type of violation event

        Returns:
            List of hooks
        """
        return self._hooks.get(event_type, [])

    def clear(self, event_type: Optional[ViolationEventType] = None) -> None:
        """
        Clear hooks.

        Args:
            event_type: Optional event type to clear (clears all if None)
        """
        if event_type is None:
            for event_type in ViolationEventType:
                self._hooks[event_type] = []
        else:
            self._hooks[event_type] = []


# Global hook registry
_hook_registry: Optional[ViolationHookRegistry] = None


def get_hook_registry() -> ViolationHookRegistry:
    """
    Get global hook registry.

    Returns:
        ViolationHookRegistry instance
    """
    global _hook_registry
    if _hook_registry is None:
        _hook_registry = ViolationHookRegistry()
    return _hook_registry


def register_violation_hook(
    event_type: ViolationEventType,
    handler: Callable[[ClarityViolation], None],
    name: Optional[str] = None,
) -> ViolationHook:
    """
    Register a violation hook globally.

    Args:
        event_type: Type of violation event
        handler: Callback function
        name: Optional name for the hook

    Returns:
        Registered hook
    """
    return get_hook_registry().register(event_type, handler, name)


def unregister_violation_hook(
    event_type: ViolationEventType,
    hook_name: str,
) -> bool:
    """
    Unregister a violation hook globally.

    Args:
        event_type: Type of violation event
        hook_name: Name of hook to unregister

    Returns:
        True if hook was unregistered
    """
    return get_hook_registry().unregister(event_type, hook_name)


def trigger_violation_hook(
    event_type: ViolationEventType,
    violation: ClarityViolation,
) -> None:
    """
    Trigger violation hooks globally.

    Args:
        event_type: Type of violation event
        violation: Violation that triggered the event
    """
    get_hook_registry().trigger(event_type, violation)


# Built-in hooks


def auto_explain_high_severity(violation: ClarityViolation) -> None:
    """
    Auto-explain violations with HIGH severity.

    Args:
        violation: Violation to explain
    """
    if violation.severity.value == "HIGH":
        logger.info(f"Auto-explaining HIGH severity violation: {violation.tool_name}")
        # In a real implementation, this would trigger auto-explanation
        # For now, just log it


def alert_critical_severity(violation: ClarityViolation) -> None:
    """
    Alert on violations with CRITICAL severity.

    Args:
        violation: Violation to alert on
    """
    # Note: ViolationSeverity only has LOW, MEDIUM, HIGH
    # This hook is for future extensibility
    if violation.severity.value == "HIGH":
        logger.warning(f"HIGH severity violation detected: {violation.tool_name}")
        # In a real implementation, this would send an alert
        # For now, just log it


def log_violation_context(violation: ClarityViolation) -> None:
    """
    Log violation context for debugging.

    Args:
        violation: Violation to log
    """
    logger.debug(f"Violation context: {violation.context}")


def register_default_hooks() -> None:
    """Register default violation hooks."""
    registry = get_hook_registry()

    # Register auto-explain hook
    registry.register(
        ViolationEventType.DETECTED,
        auto_explain_high_severity,
        name="auto_explain_high_severity",
    )

    # Register critical alert hook
    registry.register(
        ViolationEventType.DETECTED,
        alert_critical_severity,
        name="alert_critical_severity",
    )

    # Register context logging hook
    registry.register(
        ViolationEventType.LOGGED,
        log_violation_context,
        name="log_violation_context",
    )

    logger.debug("Registered default violation hooks")
