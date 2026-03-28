"""OOP wrapper for supersession-specific ledger operations.

Provides store_fact, store_event, query_facts, query_supersession_events
on top of the functional API in ledger.py. The 10 pass-through methods
that merely delegated to module-level functions have been removed.
"""

import uuid
from typing import Any

from divineos.core.ledger import (
    get_events,
    log_event,
)


class Ledger:
    """Ledger class for code that needs an object-based API.

    Provides supersession-specific operations (store_fact, query_facts, etc.)
    and delegates basic operations to the module-level functions.
    """

    def log_event(
        self, event_type: str, actor: str, payload: dict[str, Any], validate: bool = True
    ) -> str:
        return log_event(event_type, actor, payload, validate)

    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: str | None = None,
        actor: str | None = None,
    ) -> list[dict[str, Any]]:
        return get_events(limit, offset, event_type, actor)

    def store_fact(self, fact: dict[str, Any]) -> str:
        """Store a fact as a FACT_STORED event. Returns fact ID."""
        fact_id: str = fact.get("id", str(uuid.uuid4()))
        log_event("FACT_STORED", "supersession", fact, validate=False)
        return fact_id

    def store_event(self, event: dict[str, Any]) -> str:
        """Store a SUPERSESSION event. Returns event ID."""
        event_id: str = event.get("event_id", str(uuid.uuid4()))
        log_event("SUPERSESSION", "supersession", event, validate=False)
        return event_id

    def query_facts(
        self, fact_type: str | None = None, fact_key: str | None = None
    ) -> list[dict[str, Any]]:
        """Query FACT_STORED events, optionally filtering by type/key."""
        events = get_events(event_type="FACT_STORED", limit=10000)
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
        """Query SUPERSESSION events, optionally filtering by fact IDs."""
        events = get_events(event_type="SUPERSESSION", limit=10000)
        result = []
        for event in events:
            payload = event.get("payload", {})
            if superseded_fact_id and payload.get("superseded_fact_id") != superseded_fact_id:
                continue
            if superseding_fact_id and payload.get("superseding_fact_id") != superseding_fact_id:
                continue
            result.append(payload)
        return result


_ledger_instance: Ledger | None = None


def get_ledger() -> Ledger:
    """Get the global Ledger instance."""
    global _ledger_instance
    if _ledger_instance is None:
        _ledger_instance = Ledger()
    return _ledger_instance
