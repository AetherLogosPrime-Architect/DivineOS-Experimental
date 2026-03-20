"""Query interface for DivineOS supersession and contradiction resolution.

This module provides query capabilities for facts, history, and supersession chains,
allowing users to query the current truth, historical facts, and resolution chains.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FactWithHistory:
    """Represents a fact with its complete history and supersession information."""

    current_fact: Dict[str, Any]
    superseded_facts: List[Dict[str, Any]] = field(default_factory=list)
    supersession_events: List[Dict[str, Any]] = field(default_factory=list)
    history: List[Tuple[Dict[str, Any], str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_fact": self.current_fact,
            "superseded_facts": self.superseded_facts,
            "supersession_events": self.supersession_events,
            "history": [{"fact": fact, "timestamp": timestamp} for fact, timestamp in self.history],
        }


class QueryInterface:
    """Query interface for facts, history, and supersession chains."""

    def __init__(self, resolution_engine: Any, contradiction_detector: Any):
        """Initialize the query interface.

        Args:
            resolution_engine: ResolutionEngine instance
            contradiction_detector: ContradictionDetector instance
        """
        self.resolution_engine = resolution_engine
        self.contradiction_detector = contradiction_detector
        self.facts: Dict[str, Dict[str, Any]] = {}
        self.fact_history: Dict[str, List[Dict[str, Any]]] = {}

    def query_current_truth(self, fact_type: str, fact_key: str) -> Optional[FactWithHistory]:
        """Query the current truth for a fact.

        Args:
            fact_type: Type of the fact
            fact_key: Key of the fact

        Returns:
            FactWithHistory with current fact and history, or None
        """
        # Get current fact from resolution engine
        current_fact = self.resolution_engine.get_current_truth(fact_type, fact_key)

        if not current_fact:
            return None

        # Get all facts for this fact_type and fact_key
        all_facts = [
            fact
            for fact in self.facts.values()
            if fact.get("fact_type") == fact_type and fact.get("fact_key") == fact_key
        ]

        # Get superseded facts
        superseded_facts = [
            fact for fact in all_facts if self.resolution_engine.is_superseded(fact.get("id"))
        ]

        # Get supersession events for this fact
        supersession_events = []
        for fact in all_facts:
            fact_id = fact.get("id")
            chain = self.resolution_engine.get_supersession_chain(fact_id)
            for event in chain:
                supersession_events.append(event.to_dict())

        # Get history (all facts sorted by timestamp)
        history = [
            (fact, fact.get("timestamp", ""))
            for fact in sorted(all_facts, key=lambda f: f.get("timestamp", ""))
        ]

        return FactWithHistory(
            current_fact=current_fact,
            superseded_facts=superseded_facts,
            supersession_events=supersession_events,
            history=history,
        )

    def query_history(self, fact_type: str, fact_key: str) -> List[FactWithHistory]:
        """Query all facts and their history.

        Args:
            fact_type: Type of the fact
            fact_key: Key of the fact

        Returns:
            List of FactWithHistory objects
        """
        # Get all facts for this fact_type and fact_key
        all_facts = [
            fact
            for fact in self.facts.values()
            if fact.get("fact_type") == fact_type and fact.get("fact_key") == fact_key
        ]

        if not all_facts:
            return []

        # Sort by timestamp
        sorted_facts = sorted(all_facts, key=lambda f: f.get("timestamp", ""))

        # Create FactWithHistory for each fact
        results = []
        for fact in sorted_facts:
            fact_id = fact.get("id")

            # Get supersession events for this fact
            chain = self.resolution_engine.get_supersession_chain(fact_id)
            supersession_events = [event.to_dict() for event in chain]

            # Get superseded facts (facts that this fact supersedes)
            superseded_facts = [
                f
                for f in all_facts
                if self.resolution_engine.get_superseding_fact(f.get("id")) == fact_id
            ]

            results.append(
                FactWithHistory(
                    current_fact=fact,
                    superseded_facts=superseded_facts,
                    supersession_events=supersession_events,
                    history=[(f, f.get("timestamp", "")) for f in sorted_facts],
                )
            )

        return results

    def query_supersession_chain(self, fact_id: str) -> List[Dict[str, Any]]:
        """Query the supersession chain for a fact.

        Args:
            fact_id: ID of the fact

        Returns:
            List of SupersessionEvent dictionaries in the chain
        """
        chain = self.resolution_engine.get_supersession_chain(fact_id)
        return [event.to_dict() for event in chain]

    def query_contradictions(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query all contradictions.

        Args:
            severity: Optional severity filter (CRITICAL, HIGH, MEDIUM, LOW)

        Returns:
            List of contradiction dictionaries
        """
        all_contradictions = self.contradiction_detector.get_all_contradictions()

        results = []
        for contradiction in all_contradictions.values():
            if severity is None or contradiction.severity.value == severity:
                results.append(contradiction.to_dict())

        return results

    def register_fact(self, fact: Dict[str, Any]) -> None:
        """Register a fact for querying.

        Args:
            fact: Fact dictionary to register
        """
        fact_id = fact.get("id")
        if fact_id:
            self.facts[fact_id] = fact

            # Also register with resolution engine
            self.resolution_engine.register_fact(fact)

            # Track in history
            fact_type = fact.get("fact_type")
            fact_key = fact.get("fact_key")
            history_key = f"{fact_type}_{fact_key}"

            if history_key not in self.fact_history:
                self.fact_history[history_key] = []

            self.fact_history[history_key].append(fact)

    def get_fact(self, fact_id: str) -> Optional[Dict[str, Any]]:
        """Get a fact by ID.

        Args:
            fact_id: ID of the fact

        Returns:
            Fact dictionary or None
        """
        return self.facts.get(fact_id)

    def get_all_facts(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered facts.

        Returns:
            Dictionary of all facts
        """
        return self.facts.copy()

    def is_current_truth(self, fact_id: str) -> bool:
        """Check if a fact is the current truth (not superseded).

        Args:
            fact_id: ID of the fact

        Returns:
            True if fact is current truth, False otherwise
        """
        return not self.resolution_engine.is_superseded(fact_id)

    def get_superseding_fact(self, fact_id: str) -> Optional[Dict[str, Any]]:
        """Get the fact that supersedes a given fact.

        Args:
            fact_id: ID of the fact

        Returns:
            Superseding fact dictionary or None
        """
        superseding_id = self.resolution_engine.get_superseding_fact(fact_id)
        if superseding_id:
            return self.facts.get(superseding_id)
        return None

    def query_by_type(self, fact_type: str) -> List[Dict[str, Any]]:
        """Query all facts of a given type.

        Args:
            fact_type: Type of facts to query

        Returns:
            List of fact dictionaries
        """
        return [fact for fact in self.facts.values() if fact.get("fact_type") == fact_type]

    def query_current_by_type(self, fact_type: str) -> List[Dict[str, Any]]:
        """Query all current (not superseded) facts of a given type.

        Args:
            fact_type: Type of facts to query

        Returns:
            List of current fact dictionaries
        """
        return [
            fact
            for fact in self.facts.values()
            if fact.get("fact_type") == fact_type
            and (fact_id := fact.get("id")) is not None
            and self.is_current_truth(fact_id)
        ]
