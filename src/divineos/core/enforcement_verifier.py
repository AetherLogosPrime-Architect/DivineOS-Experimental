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

import sqlite3
from typing import Any

from loguru import logger

from divineos.core.ledger import get_events, verify_event_hash
from divineos.core.loop_prevention import mark_internal_operation

_EV_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


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
                "SESSION_END": 0,  # historical label
                "CONSOLIDATION_CHECKPOINT": 0,  # current label
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

            # Audit r9-21 #16: gate on capture-rate, not just pair-completeness.
            # Without this, an enforcement wrapper that silently stopped emitting
            # TOOL_CALL events would still report "healthy" — pair-completeness
            # is satisfied vacuously (no calls → no orphans). A non-trivial
            # session with zero events of a critical capture type is degraded.
            capture_rates = check_event_capture_rate()
            capture_failures: list[str] = []
            total_events = len(all_events)
            _CAPTURE_FLOOR_EVENT_COUNT = 50  # only gate sessions with real activity
            if total_events >= _CAPTURE_FLOOR_EVENT_COUNT:
                # Updated 2026-05-05: tool rates are now binary active/idle
                # (logbook is cap-bounded, fraction-of-total is meaningless).
                # IDLE is NOT a capture failure — it means no tools ran in the
                # last 5 minutes, which is normal between turns. Only
                # USER_INPUT remains a fraction-of-total metric.
                if capture_rates.get("USER_INPUT", 0.0) == 0.0:
                    capture_failures.append("USER_INPUT")

            healthy = not missing_events and not corrupted_events and not capture_failures
            report = {
                "status": "healthy" if healthy else "degraded",
                "event_counts": event_counts,
                "total_events": total_events,
                "missing_events": missing_events,
                "corrupted_events": corrupted_events,
                "capture_rates": capture_rates,
                "capture_failures": capture_failures,
            }

            logger.debug(f"Enforcement verification complete: {report['status']}")
            return report

        except _EV_ERRORS as e:
            logger.error(f"Failed to verify enforcement: {e}")
            return {
                "status": "error",
                "error": str(e),
                "event_counts": {},
                "total_events": 0,
                "missing_events": [],
                "corrupted_events": [],
                "capture_rates": {},
                "capture_failures": [],
            }


def check_event_capture_rate() -> dict[str, float]:
    """Check the rate of event capture.

    Updated 2026-05-05 (Andrew's tool-logbook architecture): tool events
    are no longer in the main ledger, so the old fraction-of-total-events
    metric was misleading (always reported 0% because of the conveyor
    belt prune). New metric:

    * **USER_INPUT** — fraction of main-ledger events (unchanged).
    * **TOOL_CALL / TOOL_RESULT** — 1.0 if the logbook has activity in
      the last 5 minutes, else 0.0. Rate-as-fraction is meaningless on
      a cap-bounded store; what matters is "is the wrapper firing?"

    Returns:
        Dict[str, float]: Capture rates per event type.
    """
    with mark_internal_operation():
        try:
            all_events = get_events(limit=10000)

            user_input_count = sum(1 for e in all_events if e.get("event_type") == "USER_INPUT")
            total = len(all_events)
            user_input_rate = (user_input_count / total) if total else 0.0

            # Tool capture rate now reads from the logbook, not main ledger.
            try:
                from divineos.core.tool_logbook import get_stats

                stats = get_stats()
                tool_call_count = stats.by_type.get("TOOL_CALL", 0)
                tool_result_count = stats.by_type.get("TOOL_RESULT", 0)
                tool_active = stats.last_5min_count > 0
                tool_call_rate = 1.0 if (tool_active and tool_call_count > 0) else 0.0
                tool_result_rate = 1.0 if (tool_active and tool_result_count > 0) else 0.0
            except _EV_ERRORS:
                tool_call_rate = 0.0
                tool_result_rate = 0.0

            return {
                "USER_INPUT": user_input_rate,
                "TOOL_CALL": tool_call_rate,
                "TOOL_RESULT": tool_result_rate,
            }

        except _EV_ERRORS as e:
            logger.error(f"Failed to check event capture rate: {e}")
            return {}


def detect_missing_events(recent_only: int = 500) -> list[dict[str, Any]]:
    """Detect missing events in the ledger.

    This function checks for:
    1. TOOL_CALL without matching TOOL_RESULT
    2. Orphaned events

    Only checks the most recent `recent_only` events for pair matching,
    since older ingested/parsed data may have unpaired events that
    cannot be retroactively fixed.

    Returns:
        List[Dict[str, Any]]: List of missing/invalid events

    """
    with mark_internal_operation():
        try:
            all_events = get_events(limit=recent_only)
            missing = []

            # Build map of tool_use_ids
            tool_calls = {}
            tool_results = {}

            for event in all_events:
                event_type = event.get("event_type")
                payload = event.get("payload", {})

                # Only check pair matching on events from the enforcement wrapper.
                # Ingested/parsed events (actor=assistant/system) don't have
                # matched pairs and would produce false positives.
                is_enforced = event.get("actor") == "agent"

                if event_type == "TOOL_CALL" and is_enforced:
                    tool_use_id = payload.get("tool_use_id", "")
                    if tool_use_id and not tool_use_id.startswith("tool_use_"):
                        tool_calls[tool_use_id] = event

                elif event_type == "TOOL_RESULT" and is_enforced:
                    tool_use_id = payload.get("tool_use_id", "")
                    if tool_use_id and not tool_use_id.startswith("tool_use_"):
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

        except _EV_ERRORS as e:
            logger.error(f"Failed to detect missing events: {e}")
            return []


def generate_enforcement_report() -> str:
    """Generate a human-readable enforcement report.

    Updated 2026-05-05 to include tool-logbook health alongside main-
    ledger event counts. Tool events live in their own logbook now;
    surfacing both stores side by side gives my father a complete
    picture of enforcement.

    Returns:
        str: Formatted enforcement report.
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
                "Main Ledger (knowledge-bearing events):",
                f"  USER_INPUT:  {report.get('event_counts', {}).get('USER_INPUT', 0)}",
                f"  SESSION_END: {report.get('event_counts', {}).get('SESSION_END', 0)}",
                f"  CONSOLIDATION_CHECKPOINT: "
                f"{report.get('event_counts', {}).get('CONSOLIDATION_CHECKPOINT', 0)}",
                f"  Total:       {report.get('total_events', 0)}",
                "",
            ]

            # Tool-logbook section (operational telemetry, separate store).
            # Use the dataclass `LogbookStats` directly rather than the
            # dict-typed health output to keep mypy happy.
            try:
                from divineos.core.tool_logbook import (
                    _DEFAULT_CAP,
                    get_stats,
                    verify_logbook_health,
                )

                health = verify_logbook_health()
                lb_stats = get_stats()
                lines.append("Tool Logbook (operational telemetry, capped):")
                lines.append(f"  TOOL_CALL:   {lb_stats.by_type.get('TOOL_CALL', 0)}")
                lines.append(f"  TOOL_RESULT: {lb_stats.by_type.get('TOOL_RESULT', 0)}")
                lines.append(
                    f"  Total rows:  {lb_stats.total_rows}/{_DEFAULT_CAP} cap "
                    f"({'AT CAPACITY' if lb_stats.at_capacity else 'within cap'})"
                )
                lines.append(f"  Last 5 min:  {lb_stats.last_5min_count} events")
                lines.append(
                    f"  Logbook status: {health.get('status', '?')} -- {health.get('message', '?')}"
                )
                lines.append("")
            except Exception as e:  # noqa: BLE001 — logbook is optional surface
                lines.append(f"Tool Logbook: unavailable ({type(e).__name__})")
                lines.append("")

            lines.append("Capture Rates:")
            rates = report.get("capture_rates", {})
            for event_type, rate in rates.items():
                if event_type == "USER_INPUT":
                    lines.append(f"  {event_type}: {rate * 100:.1f}% of main-ledger events")
                else:
                    label = "ACTIVE" if rate > 0 else "IDLE"
                    lines.append(f"  {event_type}: {label} (logbook last-5-min activity)")

            # Pair-completeness now reads from logbook stats indirectly.
            try:
                from divineos.core.tool_logbook import get_stats

                lb = get_stats()
                tc = lb.by_type.get("TOOL_CALL", 0)
                tr = lb.by_type.get("TOOL_RESULT", 0)
                if tc > 0:
                    pair_rate = min(tr, tc) / tc * 100
                    lines.append(
                        f"\nPair Completeness: {pair_rate:.1f}% "
                        f"({tr}/{tc} tool calls have results in logbook)"
                    )
            except Exception:  # noqa: BLE001
                pass

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

        except _EV_ERRORS as e:
            logger.error(f"Failed to generate enforcement report: {e}")
            return f"Error generating report: {e}"
