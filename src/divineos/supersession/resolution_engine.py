"""Resolution engine for DivineOS contradictions.

This module provides contradiction resolution capabilities, allowing the system
to automatically resolve contradictions using various strategies and create
SUPERSESSION events to track the resolution.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import hashlib
import uuid
import sqlite3
from loguru import logger

_RE_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

# Import error handling and monitoring
try:
    from divineos.integration.system_monitor import get_system_monitor

    HAS_ERROR_HANDLING = True
except ImportError:
    HAS_ERROR_HANDLING = False


class ResolutionStrategy(Enum):
    """Strategies for resolving contradictions."""

    NEWER_FACT = "newer_fact"
    HIGHER_CONFIDENCE = "higher_confidence"
    EXPLICIT_OVERRIDE = "explicit_override"


@dataclass
class SupersessionEvent:
    """Represents a supersession event (one fact supersedes another)."""

    event_id: str
    superseded_fact_id: str
    superseding_fact_id: str
    reason: str
    timestamp: str
    hash: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert supersession event to dictionary."""
        return {
            "event_id": self.event_id,
            "superseded_fact_id": self.superseded_fact_id,
            "superseding_fact_id": self.superseding_fact_id,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "hash": self.hash,
        }


class ResolutionEngine:
    """Resolves contradictions and creates SUPERSESSION events."""

    def __init__(self):
        """Initialize the resolution engine."""
        self.supersession_events: Dict[str, SupersessionEvent] = {}
        self.superseded_by: Dict[str, str] = {}  # fact_id -> superseding_fact_id
        self.facts: Dict[str, Dict[str, Any]] = {}  # fact_id -> fact

    def resolve_contradiction(
        self,
        contradiction: Any,  # Contradiction object
        resolution_strategy: ResolutionStrategy = ResolutionStrategy.NEWER_FACT,
    ) -> SupersessionEvent:
        """Resolve a contradiction and create SUPERSESSION event.

        Args:
            contradiction: Contradiction object to resolve
            resolution_strategy: Strategy to use for resolution

        Returns:
            SupersessionEvent created by resolution
        """
        import time

        start_time = time.time()
        monitor = get_system_monitor() if HAS_ERROR_HANDLING else None

        try:
            # Determine which fact supersedes which
            if resolution_strategy == ResolutionStrategy.NEWER_FACT:
                superseded_id, superseding_id = self._resolve_by_newer_fact(contradiction)
            elif resolution_strategy == ResolutionStrategy.HIGHER_CONFIDENCE:
                superseded_id, superseding_id = self._resolve_by_higher_confidence(contradiction)
            else:
                # Default to newer fact
                superseded_id, superseding_id = self._resolve_by_newer_fact(contradiction)

            # Create SUPERSESSION event
            supersession_event = self._create_supersession_event(
                superseded_id, superseding_id, resolution_strategy.value
            )

            # Store supersession event
            self.supersession_events[supersession_event.event_id] = supersession_event

            # Update superseded_by links
            self.superseded_by[superseded_id] = superseding_id

            # Record success in monitoring
            if monitor:
                latency_ms = (time.time() - start_time) * 1000
                monitor.record_latency(monitor.CONTRADICTION_RESOLUTION, latency_ms)
                monitor.record_success(monitor.CONTRADICTION_RESOLUTION)

            return supersession_event
        except _RE_ERRORS as e:
            logger.error(f"Error resolving contradiction: {e}")
            if monitor:
                monitor.record_error(monitor.CONTRADICTION_RESOLUTION, e)

            # Report unresolved contradiction to clarity enforcement
            try:
                from .clarity_integration import handle_unresolved_contradiction

                handle_unresolved_contradiction(
                    fact1_id=getattr(contradiction, "fact1_id", "unknown"),
                    fact2_id=getattr(contradiction, "fact2_id", "unknown"),
                    fact1_value=getattr(contradiction, "fact1_value", None),
                    fact2_value=getattr(contradiction, "fact2_value", None),
                    severity=getattr(contradiction, "severity", "MEDIUM"),
                    session_id="resolution-engine",
                )
            except _RE_ERRORS as e:
                logger.debug("Clarity integration failed on resolution error (best-effort): %s", e)

            raise

    def manual_resolution(
        self, superseded_fact_id: str, superseding_fact_id: str, reason: str
    ) -> SupersessionEvent:
        """Manually mark a fact as superseded.

        Args:
            superseded_fact_id: ID of the fact being superseded
            superseding_fact_id: ID of the fact that supersedes
            reason: Reason for the manual resolution

        Returns:
            SupersessionEvent created by manual resolution
        """
        # Create SUPERSESSION event
        supersession_event = self._create_supersession_event(
            superseded_fact_id, superseding_fact_id, reason
        )

        # Store supersession event
        self.supersession_events[supersession_event.event_id] = supersession_event

        # Update superseded_by links
        self.superseded_by[superseded_fact_id] = superseding_fact_id

        return supersession_event

    def get_current_truth(self, fact_type: str, fact_key: str) -> Optional[Dict[str, Any]]:
        """Get the current truth for a fact (not superseded).

        Args:
            fact_type: Type of the fact
            fact_key: Key of the fact

        Returns:
            Current fact or None
        """
        # Find all facts matching fact_type and fact_key
        matching_facts = [
            fact
            for fact in self.facts.values()
            if fact.get("fact_type") == fact_type and fact.get("fact_key") == fact_key
        ]

        if not matching_facts:
            return None

        # Filter to facts that are not superseded
        current_facts = [
            fact for fact in matching_facts if fact.get("id") not in self.superseded_by
        ]

        if not current_facts:
            return None

        # Return the most recent current fact
        return max(current_facts, key=lambda f: f.get("timestamp", ""))

    def is_superseded(self, fact_id: str) -> bool:
        """Check if a fact is superseded.

        Args:
            fact_id: ID of the fact

        Returns:
            True if fact is superseded, False otherwise
        """
        return fact_id in self.superseded_by

    def get_superseding_fact(self, fact_id: str) -> Optional[str]:
        """Get the fact that supersedes a given fact.

        Args:
            fact_id: ID of the fact

        Returns:
            ID of the superseding fact or None
        """
        return self.superseded_by.get(fact_id)

    def register_fact(self, fact: Dict[str, Any]) -> None:
        """Register a fact for tracking.

        Args:
            fact: Fact dictionary to register
        """
        fact_id = fact.get("id")
        if fact_id:
            self.facts[fact_id] = fact

    def _resolve_by_newer_fact(self, contradiction: Any) -> tuple:
        """Resolve by choosing the newer fact.

        Args:
            contradiction: Contradiction object

        Returns:
            Tuple of (superseded_fact_id, superseding_fact_id)
        """
        fact1_timestamp = contradiction.context.get("fact1", {}).get("timestamp", "")
        fact2_timestamp = contradiction.context.get("fact2", {}).get("timestamp", "")

        if fact2_timestamp > fact1_timestamp:
            return contradiction.fact1_id, contradiction.fact2_id
        else:
            return contradiction.fact2_id, contradiction.fact1_id

    def _resolve_by_higher_confidence(self, contradiction: Any) -> tuple:
        """Resolve by choosing the fact with higher confidence.

        Args:
            contradiction: Contradiction object

        Returns:
            Tuple of (superseded_fact_id, superseding_fact_id)
        """
        fact1_confidence = contradiction.context.get("fact1", {}).get("confidence", 0)
        fact2_confidence = contradiction.context.get("fact2", {}).get("confidence", 0)

        if fact2_confidence > fact1_confidence:
            return contradiction.fact1_id, contradiction.fact2_id
        elif fact1_confidence > fact2_confidence:
            return contradiction.fact2_id, contradiction.fact1_id
        else:
            # If confidence is equal, use newer fact
            return self._resolve_by_newer_fact(contradiction)

    def _create_supersession_event(
        self, superseded_fact_id: str, superseding_fact_id: str, reason: str
    ) -> SupersessionEvent:
        """Create a SUPERSESSION event.

        Args:
            superseded_fact_id: ID of the fact being superseded
            superseding_fact_id: ID of the fact that supersedes
            reason: Reason for the supersession

        Returns:
            SupersessionEvent object
        """
        event_id = f"supersession_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"

        # Create hash of the event
        event_data = f"{superseded_fact_id}_{superseding_fact_id}_{reason}_{timestamp}"
        event_hash = hashlib.sha256(event_data.encode()).hexdigest()

        return SupersessionEvent(
            event_id=event_id,
            superseded_fact_id=superseded_fact_id,
            superseding_fact_id=superseding_fact_id,
            reason=reason,
            timestamp=timestamp,
            hash=event_hash,
        )

    def get_supersession_event(self, event_id: str) -> Optional[SupersessionEvent]:
        """Get a supersession event by ID.

        Args:
            event_id: ID of the event

        Returns:
            SupersessionEvent or None
        """
        return self.supersession_events.get(event_id)

    def get_all_supersession_events(self) -> Dict[str, SupersessionEvent]:
        """Get all supersession events.

        Returns:
            Dictionary of all supersession events
        """
        return self.supersession_events.copy()

    def get_supersession_chain(self, fact_id: str) -> list:
        """Get the supersession chain for a fact.

        Args:
            fact_id: ID of the fact

        Returns:
            List of SupersessionEvent objects in the chain
        """
        chain = []
        current_id = fact_id

        while current_id in self.superseded_by:
            superseding_id = self.superseded_by[current_id]

            # Find the supersession event
            for event in self.supersession_events.values():
                if (
                    event.superseded_fact_id == current_id
                    and event.superseding_fact_id == superseding_id
                ):
                    chain.append(event)
                    break

            current_id = superseding_id

        return chain
