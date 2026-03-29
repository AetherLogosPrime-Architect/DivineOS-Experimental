"""Ledger integration for supersession and contradiction resolution.

Integrates the supersession system with the DivineOS ledger, calling
the functional API in ledger.py directly (no intermediate class wrapper).
"""

import uuid
from typing import Any, Dict, List, Optional

from loguru import logger


class LedgerIntegration:
    """Integrates supersession system with the ledger."""

    def __init__(self) -> None:
        self._available: Optional[bool] = None

    def _is_available(self) -> bool:
        if self._available is None:
            try:
                from divineos.core.ledger import log_event  # noqa: F401

                self._available = True
            except ImportError as e:
                logger.warning(f"Ledger not available (ImportError: {e})")
                self._available = False
        return self._available

    def store_fact(self, fact: Dict[str, Any]) -> Optional[str]:
        """Store a fact as a FACT_STORED event in the ledger."""
        fact_id: Optional[str] = fact.get("id")
        if fact_id is None:
            logger.warning("Cannot store fact without id")
            return None
        if not self._is_available():
            return fact_id

        from divineos.core.ledger import log_event

        log_event("FACT_STORED", "supersession", fact, validate=False)
        return fact_id

    def store_supersession_event(self, event: Dict[str, Any]) -> Optional[str]:
        """Store a SUPERSESSION event in the ledger."""
        event_id: Optional[str] = event.get("event_id", str(uuid.uuid4()))
        if not self._is_available():
            return event_id

        from divineos.core.ledger import log_event

        log_event("SUPERSESSION", "supersession", event, validate=False)
        return event_id

    def query_facts(
        self,
        fact_type: Optional[str] = None,
        fact_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query FACT_STORED events, optionally filtering by type/key."""
        if not self._is_available():
            return []

        from divineos.core.ledger import get_events

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
        superseded_fact_id: Optional[str] = None,
        superseding_fact_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query SUPERSESSION events, optionally filtering by fact IDs."""
        if not self._is_available():
            return []

        from divineos.core.ledger import get_events

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

    def update_fact_superseded_by(
        self,
        fact_id: str,
        superseding_fact_id: str,
    ) -> None:
        """Record a FACT_SUPERSEDED event linking old fact to new."""
        if not self._is_available():
            return

        from divineos.core.ledger import log_event

        log_event(
            "FACT_SUPERSEDED",
            "supersession",
            {"fact_id": fact_id, "superseded_by": superseding_fact_id},
            validate=False,
        )

    def get_fact(self, fact_id: str) -> Optional[Dict[str, Any]]:
        """Get a single fact by ID."""
        facts = self.query_facts()
        for fact in facts:
            if fact.get("id") == fact_id:
                return fact
        return None


# Global ledger integration instance
_ledger_integration: Optional[LedgerIntegration] = None


def get_ledger_integration() -> LedgerIntegration:
    """Get the global ledger integration instance.

    Returns:
        LedgerIntegration instance
    """
    global _ledger_integration
    if _ledger_integration is None:
        _ledger_integration = LedgerIntegration()
    return _ledger_integration


def store_fact(fact: Dict[str, Any]) -> Optional[str]:
    """Store a fact in the ledger.

    Args:
        fact: Fact dictionary to store

    Returns:
        Fact ID or None if missing
    """
    return get_ledger_integration().store_fact(fact)


def store_supersession_event(event: Dict[str, Any]) -> Optional[str]:
    """Store a SUPERSESSION event in the ledger.

    Args:
        event: SUPERSESSION event dictionary

    Returns:
        Event ID or None if missing
    """
    return get_ledger_integration().store_supersession_event(event)


def query_facts(
    fact_type: Optional[str] = None,
    fact_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query facts from the ledger.

    Args:
        fact_type: Optional fact type filter
        fact_key: Optional fact key filter

    Returns:
        List of fact dictionaries
    """
    return get_ledger_integration().query_facts(fact_type=fact_type, fact_key=fact_key)


def query_supersession_events(
    superseded_fact_id: Optional[str] = None,
    superseding_fact_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query SUPERSESSION events from the ledger.

    Args:
        superseded_fact_id: Optional filter for superseded fact ID
        superseding_fact_id: Optional filter for superseding fact ID

    Returns:
        List of SUPERSESSION event dictionaries
    """
    return get_ledger_integration().query_supersession_events(
        superseded_fact_id=superseded_fact_id,
        superseding_fact_id=superseding_fact_id,
    )
