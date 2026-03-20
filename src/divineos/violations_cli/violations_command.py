"""CLI commands for querying and managing contradictions and violations."""

from typing import Optional, List, Dict, Any
from enum import Enum
import json

from divineos.supersession import (
    get_ledger_integration,
)


class ViolationSeverityFilter(Enum):
    """Severity levels for filtering violations."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ViolationsCommand:
    """CLI command handler for violations and contradictions."""

    def __init__(self):
        """Initialize violations command handler."""
        self.ledger = get_ledger_integration()

    def query_violations_by_session(
        self,
        session_id: str,
        severity_filter: Optional[ViolationSeverityFilter] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query violations for a specific session.

        Args:
            session_id: Session ID to query
            severity_filter: Optional severity filter

        Returns:
            List of violations matching criteria
        """
        # Query all supersession events (which represent contradictions)
        events = self.ledger.query_supersession_events()

        violations = []
        for event in events:
            # Convert supersession event to violation format
            violation = self._event_to_violation(event, session_id)
            if violation:
                if severity_filter is None or self._matches_severity(violation, severity_filter):
                    violations.append(violation)

        return violations

    def query_recent_violations(
        self,
        limit: int = 10,
        severity_filter: Optional[ViolationSeverityFilter] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query recent violations.

        Args:
            limit: Maximum number of violations to return
            severity_filter: Optional severity filter

        Returns:
            List of recent violations
        """
        events = self.ledger.query_supersession_events()

        # Sort by timestamp (most recent first)
        sorted_events = sorted(
            events,
            key=lambda e: e.get("timestamp", ""),
            reverse=True,
        )

        violations = []
        for event in sorted_events[:limit]:
            violation = self._event_to_violation(event)
            if violation:
                if severity_filter is None or self._matches_severity(violation, severity_filter):
                    violations.append(violation)

        return violations

    def query_violations_by_severity(
        self,
        severity: ViolationSeverityFilter,
    ) -> List[Dict[str, Any]]:
        """
        Query violations filtered by severity.

        Args:
            severity: Severity level to filter by

        Returns:
            List of violations with matching severity
        """
        events = self.ledger.query_supersession_events()

        violations = []
        for event in events:
            violation = self._event_to_violation(event)
            if violation and self._matches_severity(violation, severity):
                violations.append(violation)

        return violations

    def query_contradictions(
        self,
        fact_type: Optional[str] = None,
        severity_filter: Optional[ViolationSeverityFilter] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query contradictions by fact type.

        Args:
            fact_type: Optional fact type to filter by
            severity_filter: Optional severity filter

        Returns:
            List of contradictions matching criteria
        """
        events = self.ledger.query_supersession_events()

        contradictions = []
        for event in events:
            if fact_type is None or event.get("fact_type") == fact_type:
                contradiction = self._event_to_contradiction(event)
                if contradiction:
                    if severity_filter is None or self._matches_severity(
                        contradiction, severity_filter
                    ):
                        contradictions.append(contradiction)

        return contradictions

    def format_violation_for_display(
        self,
        violation: Dict[str, Any],
    ) -> str:
        """
        Format violation for CLI display.

        Args:
            violation: Violation to format

        Returns:
            Formatted string for display
        """
        lines = [
            f"Violation ID: {violation.get('id', 'N/A')}",
            f"Severity: {violation.get('severity', 'N/A')}",
            f"Type: {violation.get('type', 'N/A')}",
            f"Timestamp: {violation.get('timestamp', 'N/A')}",
            f"Message: {violation.get('message', 'N/A')}",
        ]

        if violation.get("context"):
            lines.append(f"Context: {json.dumps(violation['context'], indent=2)}")

        return "\n".join(lines)

    def format_contradiction_for_display(
        self,
        contradiction: Dict[str, Any],
    ) -> str:
        """
        Format contradiction for CLI display.

        Args:
            contradiction: Contradiction to format

        Returns:
            Formatted string for display
        """
        lines = [
            f"Contradiction ID: {contradiction.get('id', 'N/A')}",
            f"Severity: {contradiction.get('severity', 'N/A')}",
            f"Fact Type: {contradiction.get('fact_type', 'N/A')}",
            f"Fact Key: {contradiction.get('fact_key', 'N/A')}",
            f"Fact 1: {contradiction.get('fact1_value', 'N/A')}",
            f"Fact 2: {contradiction.get('fact2_value', 'N/A')}",
            f"Timestamp: {contradiction.get('timestamp', 'N/A')}",
        ]

        return "\n".join(lines)

    def _event_to_violation(
        self,
        event: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Convert supersession event to violation format.

        Args:
            event: Supersession event
            session_id: Optional session ID to filter by

        Returns:
            Violation dict or None
        """
        if not event:
            return None

        violation = {
            "id": event.get("id"),
            "type": "CONTRADICTION",
            "severity": event.get("severity", "MEDIUM"),
            "timestamp": event.get("timestamp"),
            "message": f"Contradiction detected: {event.get('reason', 'Unknown reason')}",
            "context": {
                "superseded_fact_id": event.get("superseded_fact_id"),
                "superseding_fact_id": event.get("superseding_fact_id"),
                "reason": event.get("reason"),
            },
        }

        if session_id and event.get("session_id") != session_id:
            return None

        return violation

    def _event_to_contradiction(
        self,
        event: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Convert supersession event to contradiction format.

        Args:
            event: Supersession event

        Returns:
            Contradiction dict or None
        """
        if not event:
            return None

        return {
            "id": event.get("id"),
            "fact_type": event.get("fact_type", "unknown"),
            "fact_key": event.get("fact_key", "unknown"),
            "fact1_value": event.get("fact1_value"),
            "fact2_value": event.get("fact2_value"),
            "severity": event.get("severity", "MEDIUM"),
            "timestamp": event.get("timestamp"),
            "reason": event.get("reason"),
        }

    def _matches_severity(
        self,
        item: Dict[str, Any],
        severity_filter: ViolationSeverityFilter,
    ) -> bool:
        """
        Check if item matches severity filter.

        Args:
            item: Item to check
            severity_filter: Severity filter

        Returns:
            True if item matches filter
        """
        item_severity = item.get("severity", "MEDIUM")

        # Define severity hierarchy
        severity_order = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
        }

        item_level = severity_order.get(item_severity, 0)
        filter_level = severity_order.get(severity_filter.value, 0)

        # Return True if item severity >= filter severity
        return item_level >= filter_level


def get_violations_command() -> "ViolationsCommand":
    """
    Get singleton instance of violations command.

    Returns:
        ViolationsCommand instance
    """
    if not hasattr(get_violations_command, "_instance"):
        setattr(get_violations_command, "_instance", ViolationsCommand())
    return getattr(get_violations_command, "_instance")  # type: ignore
