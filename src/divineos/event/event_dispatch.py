"""Event Dispatch Module — Listener/callback pattern for event distribution.

Provides:
- EventDispatcher class for registering listeners and emitting events
- Module-level convenience functions: register_listener(), get_dispatcher(), emit_event()

Recursive Event Capture Prevention:
- emit_event() checks a thread-local flag from event_emission to prevent infinite loops
- When emit_event() is called while already emitting, the recursive call is skipped
"""

from typing import Any

from loguru import logger

from divineos.core.ledger import log_event
from divineos.event.event_emission import _is_in_event_emission, _set_in_event_emission


class EventDispatcher:
    """Central event emission and listener management."""

    def __init__(self) -> None:
        """Initialize the event dispatcher."""
        self.listeners: dict[str, list[Any]] = {}

    def register(self, event_type: str, callback: Any) -> None:
        """Register a listener for an event type.

        Args:
            event_type: Type of event to listen for (e.g., 'USER_INPUT')
            callback: Function to call when event is emitted
                     Signature: callback(event_type: str, payload: dict) -> None

        """
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        logger.debug(f"Registered listener for {event_type}")

    def emit(
        self,
        event_type: str,
        payload: dict[str, Any],
        actor: str = "system",
        validate: bool = True,
    ) -> str:
        """Emit an event to all listeners and log to ledger.

        Args:
            event_type: Type of event (e.g., 'USER_INPUT', 'TOOL_CALL')
            payload: Event data dict
            actor: Who triggered the event (default: 'system')
            validate: Whether to validate payload before storing (default: True)

        Returns:
            event_id: UUID of the logged event

        Raises:
            ValueError: If payload is invalid

        """
        if not isinstance(payload, dict):
            raise ValueError(f"Payload must be dict, got {type(payload)}")

        # Call registered listeners
        for callback in self.listeners.get(event_type, []):
            try:
                callback(event_type, payload)
            except Exception as e:
                logger.error(f"Listener failed for {event_type}: {e}")

        # Log to ledger
        try:
            event_id = log_event(event_type, actor, payload, validate=validate)
            logger.debug(f"Emitted {event_type} event: {event_id}")
            return event_id
        except Exception as e:
            logger.error(f"Failed to log event {event_type}: {e}")
            raise


# Global dispatcher instance
_dispatcher = EventDispatcher()


def register_listener(event_type: str, callback: Any) -> None:
    """Register a callback for an event type.

    Args:
        event_type: Type of event to listen for
        callback: Function to call when event is emitted

    """
    _dispatcher.register(event_type, callback)


def get_dispatcher() -> EventDispatcher:
    """Get the global dispatcher instance."""
    return _dispatcher


def emit_event(
    event_type: str,
    payload: dict[str, Any],
    actor: str = "system",
    validate: bool = True,
) -> str | None:
    """Emit an event to all listeners and log to ledger.

    This is a wrapper around the global dispatcher's emit method,
    providing the same interface as the original event_dispatcher module.

    Recursive Event Capture Prevention:
    - If this function is called while already emitting an event, the recursive
      call is skipped to prevent infinite loops
    - This prevents stack overflow when event listeners or ledger operations
      trigger additional events

    Args:
        event_type: Type of event (e.g., 'USER_INPUT', 'TOOL_CALL')
        payload: Event data dict
        actor: Who triggered the event (default: 'system')
        validate: Whether to validate payload before storing (default: True)

    Returns:
        event_id: UUID of the logged event, or None if recursive call was skipped

    """
    # Check for recursive event emission
    if _is_in_event_emission():
        logger.debug(f"Skipping recursive event emission: {event_type}")
        return None

    # Set flag to prevent recursive calls
    _set_in_event_emission(True)
    try:
        return _dispatcher.emit(event_type, payload, actor, validate=validate)
    finally:
        # Always clear the flag, even if an exception occurs
        _set_in_event_emission(False)
