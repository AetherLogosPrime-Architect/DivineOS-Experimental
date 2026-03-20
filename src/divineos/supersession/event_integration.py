"""Event system integration for supersession and contradiction resolution.

This module integrates the supersession system with the DivineOS event system,
allowing SUPERSESSION events to be emitted and tracked in the ledger.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from loguru import logger


@dataclass
class SupersessionEventData:
    """Data structure for SUPERSESSION events."""

    event_type: str = "SUPERSESSION"
    superseded_fact_id: str = ""
    superseding_fact_id: str = ""
    reason: str = ""
    timestamp: str = ""
    hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event emission."""
        return {
            "event_type": self.event_type,
            "superseded_fact_id": self.superseded_fact_id,
            "superseding_fact_id": self.superseding_fact_id,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "hash": self.hash,
        }


def create_supersession_event(
    superseded_fact_id: str,
    superseding_fact_id: str,
    reason: str,
) -> SupersessionEventData:
    """Create a SUPERSESSION event data structure.

    Args:
        superseded_fact_id: ID of the fact being superseded
        superseding_fact_id: ID of the fact that supersedes
        reason: Reason for the supersession

    Returns:
        SupersessionEventData object
    """
    timestamp = datetime.now(timezone.utc).isoformat() + "Z"

    # Create hash of the event
    event_data = f"{superseded_fact_id}_{superseding_fact_id}_{reason}_{timestamp}"
    event_hash = hashlib.sha256(event_data.encode()).hexdigest()

    return SupersessionEventData(
        superseded_fact_id=superseded_fact_id,
        superseding_fact_id=superseding_fact_id,
        reason=reason,
        timestamp=timestamp,
        hash=event_hash,
    )


def emit_supersession_event(
    superseded_fact_id: str,
    superseding_fact_id: str,
    reason: str,
    session_id: Optional[str] = None,
) -> str:
    """Emit a SUPERSESSION event to the event system.

    Args:
        superseded_fact_id: ID of the fact being superseded
        superseding_fact_id: ID of the fact that supersedes
        reason: Reason for the supersession
        session_id: Optional session ID

    Returns:
        Event ID of the emitted event
    """
    event_data = create_supersession_event(
        superseded_fact_id,
        superseding_fact_id,
        reason,
    )

    logger.debug(
        f"Created SUPERSESSION event: {superseded_fact_id} -> {superseding_fact_id} "
        f"(reason: {reason})"
    )

    # Return event hash as event ID
    return event_data.hash


def register_supersession_listener(callback) -> None:
    """Register a listener for SUPERSESSION events.

    Args:
        callback: Function to call when SUPERSESSION event is emitted
    """
    try:
        from divineos.event.event_emission import register_listener

        register_listener("SUPERSESSION", callback)
        logger.debug("Registered SUPERSESSION event listener")
    except Exception as e:
        logger.warning(f"Could not register SUPERSESSION listener: {e}")
