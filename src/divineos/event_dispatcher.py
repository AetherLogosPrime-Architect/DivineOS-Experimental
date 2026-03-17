"""
Event Dispatcher — Central event emission for DivineOS.

Allows registering listeners for specific event types and emitting events
that get logged to the ledger with fidelity verification.

This is the bridge between Kiro's hook system and the ledger.
"""

from typing import Callable
from loguru import logger


class EventDispatcher:
    """Central event emission and listener management."""

    def __init__(self):
        self.listeners: dict[str, list[Callable]] = {}

    def register(self, event_type: str, callback: Callable) -> None:
        """
        Register a listener for an event type.

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
        self, event_type: str, payload: dict, actor: str = "system", validate: bool = True
    ) -> str:
        """
        Emit an event to all listeners and log to ledger.

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

        # Log to ledger (import here to ensure DB path is set)
        try:
            from divineos.ledger import log_event as ledger_log_event

            event_id = ledger_log_event(event_type, actor, payload, validate=validate)
            logger.debug(f"Emitted {event_type} event: {event_id}")
            return event_id
        except Exception as e:
            logger.error(f"Failed to log event {event_type}: {e}")
            raise


# Global dispatcher instance
_dispatcher = EventDispatcher()


def emit_event(event_type: str, payload: dict, actor: str = "system", validate: bool = True) -> str:
    """
    Emit an event to all listeners and log to ledger.

    Args:
        event_type: Type of event (e.g., 'USER_INPUT', 'TOOL_CALL')
        payload: Event data dict
        actor: Who triggered the event (default: 'system')
        validate: Whether to validate payload before storing (default: True)

    Returns:
        event_id: UUID of the logged event
    """
    return _dispatcher.emit(event_type, payload, actor, validate=validate)


def register_listener(event_type: str, callback: Callable) -> None:
    """
    Register a callback for an event type.

    Args:
        event_type: Type of event to listen for
        callback: Function to call when event is emitted
    """
    _dispatcher.register(event_type, callback)


def get_dispatcher() -> EventDispatcher:
    """Get the global dispatcher instance."""
    return _dispatcher
