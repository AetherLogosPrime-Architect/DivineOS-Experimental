"""Event Integrity Verification System.

Validates event hashes and detects corrupted events in the ledger.
Provides comprehensive verification reporting.

Requirements:
- Requirement 9: Verify Event Integrity
- Requirement 9.1: Compute SHA256 hash of event payload
- Requirement 9.2: Verify hash matches stored hash
- Requirement 9.3: Mark event as corrupted if hash verification fails
- Requirement 9.4: Check all events for hash validity
- Requirement 9.5: Report any corrupted events
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from divineos.core.ledger import (
    _get_connection,
    verify_event_hash,
)


@dataclass
class VerificationReport:
    """Report of event integrity verification."""

    total_events: int = 0
    valid_events: int = 0
    corrupted_events: int = 0
    corrupted_event_ids: list[str] = field(default_factory=list)
    corrupted_event_details: list[dict[str, Any]] = field(default_factory=list)
    verification_timestamp: str = ""
    verification_status: str = "PENDING"

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "total_events": self.total_events,
            "valid_events": self.valid_events,
            "corrupted_events": self.corrupted_events,
            "corrupted_event_ids": self.corrupted_event_ids,
            "corrupted_event_details": self.corrupted_event_details,
            "verification_timestamp": self.verification_timestamp,
            "verification_status": self.verification_status,
        }

    def to_markdown(self) -> str:
        """Convert report to markdown format."""
        lines = [
            "# Event Integrity Verification Report",
            "",
            f"**Verification Timestamp:** {self.verification_timestamp}",
            f"**Status:** {self.verification_status}",
            "",
            "## Summary",
            "",
            f"- **Total Events:** {self.total_events}",
            f"- **Valid Events:** {self.valid_events}",
            f"- **Corrupted Events:** {self.corrupted_events}",
            "",
        ]

        if self.corrupted_events > 0:
            lines.extend(
                [
                    "## Corrupted Events",
                    "",
                ],
            )
            for detail in self.corrupted_event_details:
                lines.append(f"### Event {detail['event_id']}")
                lines.append("")
                lines.append(f"- **Type:** {detail['event_type']}")
                lines.append(f"- **Reason:** {detail['reason']}")
                lines.append("")
        else:
            lines.extend(
                [
                    "## Status",
                    "",
                    "✓ All events verified successfully. No corruption detected.",
                    "",
                ],
            )

        return "\n".join(lines)


class EventVerifier:
    """Verify event integrity in the ledger."""

    def __init__(self) -> None:
        """Initialize the event verifier."""
        self.logger = logger

    def verify_all_events(self) -> VerificationReport:
        """Verify all events in the ledger.

        Checks that each event's content_hash matches the hash of its payload.
        Identifies and reports any corrupted events.

        Returns:
            VerificationReport: Detailed verification report

        Requirements:
            - Requirement 9.4: Check all events for hash validity
            - Requirement 9.5: Report any corrupted events

        """
        report = VerificationReport()
        report.verification_timestamp = datetime.now(timezone.utc).isoformat()

        conn = _get_connection()
        try:
            cursor = conn.execute(
                "SELECT event_id, event_type, payload, content_hash FROM system_events",
            )
            rows = cursor.fetchall()

            report.total_events = len(rows)

            for row in rows:
                event_id, event_type, payload_json, stored_hash = row
                payload = json.loads(payload_json)

                is_valid = self._verify_event(event_id, event_type, payload, stored_hash)

                if is_valid:
                    report.valid_events += 1
                else:
                    report.corrupted_events += 1
                    report.corrupted_event_ids.append(event_id)

                    # Get detailed reason for corruption
                    _is_hash_valid, reason = verify_event_hash(event_id, payload, stored_hash)

                    report.corrupted_event_details.append(
                        {
                            "event_id": event_id,
                            "event_type": event_type,
                            "reason": reason,
                        },
                    )

                    self.logger.error(f"Event corrupted: {event_id} ({event_type}) - {reason}")

            # Set verification status
            if report.corrupted_events == 0:
                report.verification_status = "PASS"
            else:
                report.verification_status = "FAIL"

            self.logger.info(
                f"Event verification complete: {report.valid_events}/{report.total_events} valid",
            )

            return report

        finally:
            conn.close()

    def verify_event(self, event_id: str) -> tuple[bool, str]:
        """Verify a single event by ID.

        Args:
            event_id: The event ID to verify

        Returns:
            tuple: (is_valid, reason)

        Requirements:
            - Requirement 9.2: Verify hash matches stored hash

        """
        conn = _get_connection()
        try:
            cursor = conn.execute(
                "SELECT event_type, payload, content_hash FROM system_events WHERE event_id = ?",
                (event_id,),
            )
            row = cursor.fetchone()

            if not row:
                return False, f"Event not found: {event_id}"

            _event_type, payload_json, stored_hash = row
            payload = json.loads(payload_json)

            is_valid, reason = verify_event_hash(event_id, payload, stored_hash)
            return is_valid, reason

        finally:
            conn.close()

    def detect_corrupted_events(self) -> list[dict[str, Any]]:
        """Detect all corrupted events in the ledger.

        Returns:
            list: List of corrupted event details

        Requirements:
            - Requirement 9.3: Identify events with invalid hashes
            - Requirement 9.3: Identify events with missing hashes
            - Requirement 9.3: Identify events with malformed data

        """
        corrupted: list[dict[str, Any]] = []

        conn = _get_connection()
        try:
            cursor = conn.execute(
                "SELECT event_id, event_type, payload, content_hash FROM system_events",
            )
            rows = cursor.fetchall()

            for row in rows:
                event_id, event_type, payload_json, stored_hash = row

                # Check for missing hash
                if not stored_hash:
                    corrupted.append(
                        {
                            "event_id": event_id,
                            "event_type": event_type,
                            "corruption_type": "missing_hash",
                            "reason": "Event has no stored hash",
                        },
                    )
                    self.logger.warning(f"Event missing hash: {event_id}")
                    continue

                # Check for malformed payload
                try:
                    payload = json.loads(payload_json)
                except json.JSONDecodeError as e:
                    corrupted.append(
                        {
                            "event_id": event_id,
                            "event_type": event_type,
                            "corruption_type": "malformed_payload",
                            "reason": f"Invalid JSON: {e!s}",
                        },
                    )
                    self.logger.warning(f"Event malformed payload: {event_id}")
                    continue

                # Check for hash mismatch
                is_valid, reason = verify_event_hash(event_id, payload, stored_hash)
                if not is_valid:
                    corrupted.append(
                        {
                            "event_id": event_id,
                            "event_type": event_type,
                            "corruption_type": "hash_mismatch",
                            "reason": reason,
                        },
                    )
                    self.logger.warning(f"Event hash mismatch: {event_id}")

            return corrupted

        finally:
            conn.close()

    def generate_verification_report(self) -> VerificationReport:
        """Generate comprehensive verification report.

        Includes:
        - Total events verified
        - Valid events count
        - Corrupted events count
        - List of corrupted event IDs
        - Verification timestamp
        - Detailed corruption reasons

        Returns:
            VerificationReport: Comprehensive verification report

        Requirements:
            - Requirement 9.4: Generate verification report with total events
            - Requirement 9.5: Generate verification report with valid/corrupted counts
            - Requirement 9.5: Generate verification report with corrupted event IDs

        """
        return self.verify_all_events()

    def _verify_event(
        self,
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
        stored_hash: str,
    ) -> bool:
        """Internal method to verify a single event.

        Args:
            event_id: The event ID
            event_type: The event type
            payload: The event payload
            stored_hash: The stored hash

        Returns:
            bool: True if event is valid, False if corrupted

        """
        is_valid, _ = verify_event_hash(event_id, payload, stored_hash)
        return is_valid
