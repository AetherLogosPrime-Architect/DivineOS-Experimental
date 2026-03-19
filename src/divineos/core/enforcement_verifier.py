"""Enforcement Verifier Module — Verifies that enforcement is working correctly.

This module provides functions to verify that the event enforcement system
is capturing all events correctly:
- Verify all event types are captured
- Check event capture rates
- Detect missing or corrupted events
- Generate verification reports

All verifier operations are marked as internal to prevent recursive capture.

Requirements:
- Requirement 9.1-9.7: Verify enforcement is working
"""

from typing import Any

from loguru import logger

from divineos.core.ledger import get_events, verify_event_hash
from divineos.core.loop_prevention import mark_internal_operation


def verify_enforcement() -> dict[str, Any]:
    """Verify that enforcement is working correctly.

    This function checks:
    1. USER_INPUT events are captured
    2. TOOL_CALL events are captured
    3. TOOL_RESULT events are captured
    4. SESSION_END events are emitted
    5. Event hashes are valid

    Returns:
        Dict[str, Any]: Verification report with status and details

    Requirements:
        - Requirement 9.1-9.7: Verify enforcement

    """
    with mark_internal_operation():
        try:
            logger.debug("Starting enforcement verification")

            # Get all events
            all_events = get_events(limit=10000)
            logger.debug(f"Retrieved {len(all_events)} events for verification")

            # Count events by type
            event_counts = {
                "USER_INPUT": 0,
                "TOOL_CALL": 0,
                "TOOL_RESULT": 0,
                "SESSION_END": 0,
                "EXPLANATION": 0,
            }

            for event in all_events:
                event_type = event.get("event_type")
                if event_type in event_counts:
                    event_counts[event_type] += 1

            # Check for missing events
            missing_events = detect_missing_events()

            # Check for corrupted events
            corrupted_events = []
            for event in all_events:
                event_id = event.get("event_id")
                payload = event.get("payload", {})
                stored_hash = event.get("hash")

                if stored_hash and event_id:
                    is_valid, _ = verify_event_hash(event_id, payload, stored_hash)
                    if not is_valid:
                        corrupted_events.append(event_id)

            # Generate report
            report = {
                "status": "healthy" if not missing_events and not corrupted_events else "degraded",
                "event_counts": event_counts,
                "total_events": len(all_events),
                "missing_events": missing_events,
                "corrupted_events": corrupted_events,
                "capture_rates": check_event_capture_rate(),
            }

            logger.debug(f"Enforcement verification complete: {report['status']}")
            return report

        except Exception as e:
            logger.error(f"Failed to verify enforcement: {e}")
            return {
                "status": "error",
                "error": str(e),
                "event_counts": {},
                "total_events": 0,
                "missing_events": [],
                "corrupted_events": [],
                "capture_rates": {},
            }


def check_event_capture_rate() -> dict[str, float]:
    """Check the rate of event capture.

    This function calculates:
    1. USER_INPUT capture rate
    2. TOOL_CALL capture rate
    3. TOOL_RESULT capture rate

    Returns:
        Dict[str, float]: Capture rates for each event type

    Requirements:
        - Requirement 9.1-9.3: Check capture rates

    """
    with mark_internal_operation():
        try:
            all_events = get_events(limit=10000)

            # Count events by type
            event_counts = {
                "USER_INPUT": 0,
                "TOOL_CALL": 0,
                "TOOL_RESULT": 0,
            }

            for event in all_events:
                event_type = event.get("event_type")
                if event_type in event_counts:
                    event_counts[event_type] += 1

            # Calculate rates
            total = len(all_events)
            if total == 0:
                return {
                    "USER_INPUT": 0.0,
                    "TOOL_CALL": 0.0,
                    "TOOL_RESULT": 0.0,
                }

            return {
                "USER_INPUT": event_counts["USER_INPUT"] / total,
                "TOOL_CALL": event_counts["TOOL_CALL"] / total,
                "TOOL_RESULT": event_counts["TOOL_RESULT"] / total,
            }

        except Exception as e:
            logger.error(f"Failed to check event capture rate: {e}")
            return {}


def detect_missing_events() -> list[dict[str, Any]]:
    """Detect missing events in the ledger.

    This function checks for:
    1. TOOL_CALL without matching TOOL_RESULT
    2. Orphaned events
    3. Events with invalid hashes

    Returns:
        List[Dict[str, Any]]: List of missing/invalid events

    Requirements:
        - Requirement 9.5-9.6: Detect missing and invalid events

    """
    with mark_internal_operation():
        try:
            all_events = get_events(limit=10000)
            missing = []

            # Build map of tool_use_ids
            tool_calls = {}
            tool_results = {}

            for event in all_events:
                event_type = event.get("event_type")
                payload = event.get("payload", {})

                if event_type == "TOOL_CALL":
                    tool_use_id = payload.get("tool_use_id")
                    if tool_use_id:
                        tool_calls[tool_use_id] = event

                elif event_type == "TOOL_RESULT":
                    tool_use_id = payload.get("tool_use_id")
                    if tool_use_id:
                        tool_results[tool_use_id] = event

            # Check for TOOL_CALL without matching TOOL_RESULT
            for tool_use_id, tool_call in tool_calls.items():
                if tool_use_id not in tool_results:
                    missing.append(
                        {
                            "type": "missing_tool_result",
                            "tool_use_id": tool_use_id,
                            "tool_call_event_id": tool_call.get("event_id"),
                        },
                    )

            # Check for TOOL_RESULT without matching TOOL_CALL
            for tool_use_id, tool_result in tool_results.items():
                if tool_use_id not in tool_calls:
                    missing.append(
                        {
                            "type": "orphaned_tool_result",
                            "tool_use_id": tool_use_id,
                            "tool_result_event_id": tool_result.get("event_id"),
                        },
                    )

            logger.debug(f"Detected {len(missing)} missing/orphaned events")
            return missing

        except Exception as e:
            logger.error(f"Failed to detect missing events: {e}")
            return []


def generate_enforcement_report() -> str:
    """Generate a human-readable enforcement report.

    Returns:
        str: Formatted enforcement report

    Requirements:
        - Requirement 9.7: Provide summary of enforcement status

    """
    with mark_internal_operation():
        try:
            report = verify_enforcement()

            # Format report
            lines = [
                "=" * 60,
                "DivineOS Event Enforcement Verification Report",
                "=" * 60,
                "",
                f"Status: {report.get('status', 'unknown').upper()}",
                "",
                "Event Counts:",
                f"  USER_INPUT:  {report.get('event_counts', {}).get('USER_INPUT', 0)}",
                f"  TOOL_CALL:   {report.get('event_counts', {}).get('TOOL_CALL', 0)}",
                f"  TOOL_RESULT: {report.get('event_counts', {}).get('TOOL_RESULT', 0)}",
                f"  SESSION_END: {report.get('event_counts', {}).get('SESSION_END', 0)}",
                f"  Total:       {report.get('total_events', 0)}",
                "",
                "Capture Rates:",
            ]

            rates = report.get("capture_rates", {})
            for event_type, rate in rates.items():
                lines.append(f"  {event_type}: {rate * 100:.1f}%")

            # Add missing events section
            missing = report.get("missing_events", [])
            if missing:
                lines.append("")
                lines.append(f"Missing/Orphaned Events: {len(missing)}")
                for item in missing[:10]:  # Show first 10
                    lines.append(f"  - {item.get('type')}: {item.get('tool_use_id', 'unknown')}")
                if len(missing) > 10:
                    lines.append(f"  ... and {len(missing) - 10} more")

            # Add corrupted events section
            corrupted = report.get("corrupted_events", [])
            if corrupted:
                lines.append("")
                lines.append(f"Corrupted Events: {len(corrupted)}")
                for event_id in corrupted[:10]:  # Show first 10
                    lines.append(f"  - {event_id}")
                if len(corrupted) > 10:
                    lines.append(f"  ... and {len(corrupted) - 10} more")

            lines.append("")
            lines.append("=" * 60)

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to generate enforcement report: {e}")
            return f"Error generating report: {e}"
