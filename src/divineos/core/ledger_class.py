"""OOP wrapper around the ledger module-level functions.

Provides a class-based API for ledger operations, enabling integration
with systems that expect a Ledger class (like ledger_integration.py).
Delegates to the module-level functions in ledger.py.
"""

import uuid
from typing import Any

from divineos.core.ledger import (
    count_events,
    clean_corrupted_events,
    export_to_markdown,
    get_events,
    get_recent_context,
    get_verified_events,
    log_event,
    search_events,
    verify_all_events,
    verify_event_hash,
)


class Ledger:
    """Object-oriented wrapper around ledger module-level functions.

    Provides a class-based API for ledger operations, enabling integration
    with systems that expect a Ledger class (like ledger_integration.py).

    This wrapper delegates to the module-level functions, maintaining backward
    compatibility while providing a cleaner OOP interface.
    """

    def log_event(
        self, event_type: str, actor: str, payload: dict[str, Any], validate: bool = True
    ) -> str:
        """Log an event to the ledger.

        Args:
            event_type: Type of event (e.g., 'USER_INPUT', 'TOOL_CALL')
            actor: Who triggered the event (e.g., 'user', 'assistant')
            payload: Event data
            validate: Whether to validate payload before storing

        Returns:
            Event ID
        """
        return log_event(event_type, actor, payload, validate)

    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: str | None = None,
        actor: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get events from the ledger.

        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip
            event_type: Optional filter by event type
            actor: Optional filter by actor

        Returns:
            List of event dictionaries
        """
        return get_events(limit, offset, event_type, actor)

    def search_events(self, keyword: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search events by keyword.

        Args:
            keyword: Search term
            limit: Maximum number of results

        Returns:
            List of matching events
        """
        return search_events(keyword, limit)

    def get_recent_context(self, n: int = 20) -> list[dict[str, Any]]:
        """Get recent events for context.

        Args:
            n: Number of recent events to return

        Returns:
            List of recent events in chronological order
        """
        return get_recent_context(n)

    def count_events(self) -> dict[str, Any]:
        """Count events by type and actor.

        Returns:
            Dictionary with event counts
        """
        return count_events()

    def verify_event_hash(
        self, event_id: str, payload: dict[str, Any], stored_hash: str
    ) -> tuple[bool, str]:
        """Verify an event's hash.

        Args:
            event_id: Event ID (for logging)
            payload: Event payload
            stored_hash: Stored hash to verify against

        Returns:
            Tuple of (is_valid, reason)
        """
        return verify_event_hash(event_id, payload, stored_hash)

    def get_verified_events(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: str | None = None,
        actor: str | None = None,
        session_id: str | None = None,
        skip_corrupted: bool = True,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Get events with hash verification.

        Args:
            limit: Maximum number of events
            offset: Number of events to skip
            event_type: Optional filter by event type
            actor: Optional filter by actor
            session_id: Optional filter by session
            skip_corrupted: Whether to exclude corrupted events

        Returns:
            Tuple of (verified_events, corrupted_events)
        """
        return get_verified_events(limit, offset, event_type, actor, session_id, skip_corrupted)

    def verify_all_events(self) -> dict[str, Any]:
        """Verify integrity of all events.

        Returns:
            Dictionary with verification results
        """
        return verify_all_events()

    def clean_corrupted_events(self) -> dict[str, Any]:
        """Remove corrupted events from the ledger.

        Returns:
            Dictionary with cleanup results
        """
        return clean_corrupted_events()

    def export_to_markdown(self) -> str:
        """Export all events to markdown.

        Returns:
            Markdown string
        """
        return export_to_markdown()

    def store_fact(self, fact: dict[str, Any]) -> str:
        """Store a fact in the ledger.

        Args:
            fact: Fact dictionary with 'id' key

        Returns:
            Fact ID
        """
        fact_id: str = fact.get("id", str(uuid.uuid4()))
        self.log_event("FACT_STORED", "supersession", fact, validate=False)
        return fact_id

    def store_event(self, event: dict[str, Any]) -> str:
        """Store an event in the ledger.

        Args:
            event: Event dictionary with 'event_id' key

        Returns:
            Event ID
        """
        event_id: str = event.get("event_id", str(uuid.uuid4()))
        self.log_event("SUPERSESSION", "supersession", event, validate=False)
        return event_id

    def query_facts(
        self, fact_type: str | None = None, fact_key: str | None = None
    ) -> list[dict[str, Any]]:
        """Query facts from the ledger.

        Args:
            fact_type: Optional filter by fact type
            fact_key: Optional filter by fact key

        Returns:
            List of facts
        """
        events = self.get_events(event_type="FACT_STORED", limit=10000)
        facts = []
        for event in events:
            payload = event.get("payload", {})
            if fact_type and payload.get("fact_type") != fact_type:
                continue
            if fact_key and payload.get("fact_key") != fact_key:
                continue
            facts.append(payload)
        return facts

    def query_supersession_events(
        self,
        superseded_fact_id: str | None = None,
        superseding_fact_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query supersession events from the ledger.

        Args:
            superseded_fact_id: Optional filter by superseded fact ID
            superseding_fact_id: Optional filter by superseding fact ID

        Returns:
            List of supersession events
        """
        events = self.get_events(event_type="SUPERSESSION", limit=10000)
        supersession_events = []
        for event in events:
            payload = event.get("payload", {})
            if superseded_fact_id and payload.get("superseded_fact_id") != superseded_fact_id:
                continue
            if superseding_fact_id and payload.get("superseding_fact_id") != superseding_fact_id:
                continue
            supersession_events.append(payload)
        return supersession_events


# Global ledger instance
_ledger_instance: Ledger | None = None


def get_ledger() -> Ledger:
    """Get the global Ledger instance.

    Returns:
        Ledger instance
    """
    global _ledger_instance
    if _ledger_instance is None:
        _ledger_instance = Ledger()
    return _ledger_instance
