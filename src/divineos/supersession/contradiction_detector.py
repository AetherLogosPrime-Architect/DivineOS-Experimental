"""Contradiction detection system for DivineOS.

This module provides contradiction detection capabilities, allowing the system
to identify when two facts contradict each other, classify the severity of the
contradiction, and capture full context for resolution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class ContradictionSeverity(Enum):
    """Severity levels for contradictions."""

    CRITICAL = "CRITICAL"  # Mathematical, security facts
    HIGH = "HIGH"  # State, configuration facts
    MEDIUM = "MEDIUM"  # Metadata, timing facts
    LOW = "LOW"  # Informational, derived facts


@dataclass
class Contradiction:
    """Represents a contradiction between two facts."""

    fact1_id: str
    fact2_id: str
    fact1_value: Any
    fact2_value: Any
    severity: ContradictionSeverity
    timestamp: str
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert contradiction to dictionary."""
        return {
            "fact1_id": self.fact1_id,
            "fact2_id": self.fact2_id,
            "fact1_value": self.fact1_value,
            "fact2_value": self.fact2_value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "context": self.context,
        }


class ContradictionDetector:
    """Detects contradictions between facts."""

    def __init__(self):
        """Initialize the contradiction detector."""
        self.contradictions: Dict[str, Contradiction] = {}

    def detect_contradiction(
        self, fact1: Dict[str, Any], fact2: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Optional[Contradiction]:
        """Detect if two facts contradict each other.

        Args:
            fact1: First fact dictionary
            fact2: Second fact dictionary
            context: Additional context for the contradiction

        Returns:
            Contradiction object if detected, None otherwise
        """
        if context is None:
            context = {}

        # Extract values
        fact1_value = fact1.get("value")
        fact2_value = fact2.get("value")
        fact1_id = fact1.get("id", "unknown")
        fact2_id = fact2.get("id", "unknown")

        # Check if values are different (contradiction)
        if fact1_value == fact2_value:
            return None

        # Check if facts are about the same thing
        fact1_type = fact1.get("fact_type")
        fact2_type = fact2.get("fact_type")
        fact1_key = fact1.get("fact_key")
        fact2_key = fact2.get("fact_key")

        if fact1_type != fact2_type or fact1_key != fact2_key:
            return None

        # Classify severity
        severity = self.classify_severity(fact1, fact2)

        # Create contradiction
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        contradiction = Contradiction(
            fact1_id=fact1_id,
            fact2_id=fact2_id,
            fact1_value=fact1_value,
            fact2_value=fact2_value,
            severity=severity,
            timestamp=timestamp,
            context=self.capture_context(fact1, fact2, context),
        )

        # Store contradiction
        contradiction_id = f"{fact1_id}_{fact2_id}"
        self.contradictions[contradiction_id] = contradiction

        return contradiction

    def classify_severity(
        self, fact1: Dict[str, Any], fact2: Dict[str, Any]
    ) -> ContradictionSeverity:
        """Classify contradiction severity.

        Args:
            fact1: First fact
            fact2: Second fact

        Returns:
            ContradictionSeverity level
        """
        fact_type = fact1.get("fact_type", "")

        # CRITICAL: Mathematical, security facts
        if fact_type in ["mathematical_operation", "security_check", "cryptographic_hash"]:
            return ContradictionSeverity.CRITICAL

        # HIGH: State, configuration facts
        if fact_type in ["system_state", "configuration", "deployment_status"]:
            return ContradictionSeverity.HIGH

        # MEDIUM: Metadata, timing facts
        if fact_type in ["metadata", "timing", "performance_metric"]:
            return ContradictionSeverity.MEDIUM

        # LOW: Informational, derived facts
        return ContradictionSeverity.LOW

    def capture_context(
        self,
        fact1: Dict[str, Any],
        fact2: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Capture full contradiction context.

        Args:
            fact1: First fact
            fact2: Second fact
            additional_context: Additional context to include

        Returns:
            Dictionary with full context
        """
        if additional_context is None:
            additional_context = {}

        context = {
            "fact1": {
                "id": fact1.get("id"),
                "type": fact1.get("fact_type"),
                "key": fact1.get("fact_key"),
                "value": fact1.get("value"),
                "timestamp": fact1.get("timestamp"),
                "source": fact1.get("source"),
                "confidence": fact1.get("confidence"),
            },
            "fact2": {
                "id": fact2.get("id"),
                "type": fact2.get("fact_type"),
                "key": fact2.get("fact_key"),
                "value": fact2.get("value"),
                "timestamp": fact2.get("timestamp"),
                "source": fact2.get("source"),
                "confidence": fact2.get("confidence"),
            },
            "additional": additional_context,
        }

        return context

    def get_contradiction(self, contradiction_id: str) -> Optional[Contradiction]:
        """Get a stored contradiction by ID.

        Args:
            contradiction_id: ID of the contradiction

        Returns:
            Contradiction object or None
        """
        return self.contradictions.get(contradiction_id)

    def get_all_contradictions(self) -> Dict[str, Contradiction]:
        """Get all stored contradictions.

        Returns:
            Dictionary of all contradictions
        """
        return self.contradictions.copy()

    def clear_contradictions(self) -> None:
        """Clear all stored contradictions."""
        self.contradictions.clear()
