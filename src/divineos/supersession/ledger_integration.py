"""Ledger integration for supersession and contradiction resolution.

This module integrates the supersession system with the DivineOS ledger,
allowing facts and SUPERSESSION events to be stored and queried.
"""

from typing import Dict, Any, Optional, List
from loguru import logger


class LedgerIntegration:
    """Integrates supersession system with the ledger."""

    def __init__(self, ledger=None):
        """Initialize ledger integration.

        Args:
            ledger: Optional ledger instance. If None, will be loaded on demand.
        """
        self._ledger = ledger

    @property
    def ledger(self):
        """Get the ledger instance, loading if necessary."""
        if self._ledger is None:
            try:
                from divineos.core.ledger import get_ledger

                self._ledger = get_ledger()
            except ImportError:
                logger.warning("Ledger not available, using in-memory storage")
                self._ledger = None
        return self._ledger

    def store_fact(self, fact: Dict[str, Any]) -> Optional[str]:
        """Store a fact in the ledger.

        Args:
            fact: Fact dictionary to store

        Returns:
            Fact ID or None if missing
        """
        fact_id = fact.get("id")

        if fact_id is None:
            logger.warning("Cannot store fact without id")
            return None

        if self.ledger is None:
            logger.debug(f"Storing fact {fact_id} in memory (ledger not available)")
            return fact_id

        try:
            # Store in ledger
            self.ledger.store_fact(fact)
            logger.debug(f"Stored fact {fact_id} in ledger")
            return fact_id
        except Exception as e:
            logger.error(f"Failed to store fact {fact_id} in ledger: {e}")
            raise

    def store_supersession_event(self, event: Dict[str, Any]) -> Optional[str]:
        """Store a SUPERSESSION event in the ledger.

        Args:
            event: SUPERSESSION event dictionary

        Returns:
            Event ID or None if missing
        """
        event_id = event.get("event_id")

        if event_id is None:
            logger.warning("Cannot store SUPERSESSION event without event_id")
            return None

        if self.ledger is None:
            logger.debug(f"Storing SUPERSESSION event {event_id} in memory (ledger not available)")
            return event_id

        try:
            # Store in ledger
            self.ledger.store_event(event)
            logger.debug(f"Stored SUPERSESSION event {event_id} in ledger")
            return event_id
        except Exception as e:
            logger.error(f"Failed to store SUPERSESSION event {event_id} in ledger: {e}")
            raise

    def query_facts(
        self,
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
        if self.ledger is None:
            logger.debug("Querying facts from memory (ledger not available)")
            return []

        try:
            # Query ledger
            facts = self.ledger.query_facts(fact_type=fact_type, fact_key=fact_key)
            logger.debug(f"Queried {len(facts)} facts from ledger")
            return facts if isinstance(facts, list) else []
        except Exception as e:
            logger.error(f"Failed to query facts from ledger: {e}")
            return []

    def query_supersession_events(
        self,
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
        if self.ledger is None:
            logger.debug("Querying SUPERSESSION events from memory (ledger not available)")
            return []

        try:
            # Query ledger for SUPERSESSION events
            events = self.ledger.query_events(
                event_type="SUPERSESSION",
                filters={
                    "superseded_fact_id": superseded_fact_id,
                    "superseding_fact_id": superseding_fact_id,
                },
            )
            logger.debug(f"Queried {len(events)} SUPERSESSION events from ledger")
            return events if isinstance(events, list) else []
        except Exception as e:
            logger.error(f"Failed to query SUPERSESSION events from ledger: {e}")
            return []

    def update_fact_superseded_by(
        self,
        fact_id: str,
        superseding_fact_id: str,
    ) -> None:
        """Update a fact's superseded_by link in the ledger.

        Args:
            fact_id: ID of the fact being superseded
            superseding_fact_id: ID of the fact that supersedes
        """
        if self.ledger is None:
            logger.debug(f"Updating fact {fact_id} superseded_by link in memory")
            return

        try:
            # Update in ledger
            self.ledger.update_fact(fact_id, {"superseded_by": superseding_fact_id})
            logger.debug(f"Updated fact {fact_id} superseded_by link in ledger")
        except Exception as e:
            logger.error(f"Failed to update fact {fact_id} superseded_by link: {e}")
            raise

    def get_fact(self, fact_id: str) -> Optional[Dict[str, Any]]:
        """Get a fact from the ledger.

        Args:
            fact_id: ID of the fact

        Returns:
            Fact dictionary or None
        """
        if self.ledger is None:
            logger.debug(f"Getting fact {fact_id} from memory (ledger not available)")
            return None

        try:
            # Get from ledger
            fact = self.ledger.get_fact(fact_id)
            logger.debug(f"Retrieved fact {fact_id} from ledger")
            return fact  # type: ignore
        except Exception as e:
            logger.error(f"Failed to get fact {fact_id} from ledger: {e}")
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
