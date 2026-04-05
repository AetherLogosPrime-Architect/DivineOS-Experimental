"""Thread-local context for recursive event capture prevention."""

import threading

_event_emission_context = threading.local()


def _is_in_event_emission() -> bool:
    """Check if we're currently in event emission (recursive call detection)."""
    return getattr(_event_emission_context, "in_emission", False)


def _set_in_event_emission(value: bool) -> None:
    """Set the event emission flag."""
    _event_emission_context.in_emission = value
