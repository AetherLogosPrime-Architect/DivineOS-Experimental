"""Ledger Integration.

Integrates with the existing DivineOS ledger for querying execution events.
"""

from typing import Any
from uuid import UUID

from loguru import logger

from divineos.core import ledger

from .types import ExecutionData, ExecutionMetrics, ToolCall


class LedgerQueryInterface:
    """Interface for querying the ledger for execution data."""

    @staticmethod
    def query_events_for_session(
        session_id: UUID,
        event_type: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Query ledger for events in a session.

        Args:
            session_id: Session ID to query
            event_type: Optional event type filter
            limit: Maximum number of events to return

        Returns:
            List of events from ledger

        """
        try:
            # Convert UUID to string for ledger query
            session_id_str = str(session_id)

            # Query ledger with session filter
            verified_events, corrupted_events = ledger.get_verified_events(
                limit=limit,
                event_type=event_type,
                session_id=session_id_str,
                skip_corrupted=True,
            )

            if corrupted_events:
                logger.warning(
                    f"Found {len(corrupted_events)} corrupted events for session {session_id}",
                )

            logger.info(
                f"Queried ledger for session {session_id}: {len(verified_events)} verified events",
            )
            return verified_events

        except Exception as e:
            logger.error(f"Error querying ledger for session {session_id}: {e}")
            return []

    @staticmethod
    def extract_tool_calls_from_events(events: list[dict[str, Any]]) -> list[ToolCall]:
        """Extract tool calls from ledger events.

        Args:
            events: List of events from ledger

        Returns:
            List of ToolCall objects

        """
        try:
            tool_calls = []

            for event in events:
                try:
                    # Look for TOOL_CALL events
                    if event.get("event_type") == "TOOL_CALL":
                        payload = event.get("payload", {})
                        tool_call = ToolCall(
                            tool_name=payload.get("tool_name", "unknown"),
                            timestamp=event.get("timestamp", ""),
                            input=payload.get("tool_input", {}),
                        )
                        tool_calls.append(tool_call)
                except Exception as e:
                    logger.warning(f"Error extracting tool call from event: {e}")

            logger.info(f"Extracted {len(tool_calls)} tool calls from {len(events)} events")
            return tool_calls

        except Exception as e:
            logger.error(f"Error extracting tool calls: {e}")
            return []

    @staticmethod
    def extract_errors_from_events(events: list[dict[str, Any]]) -> list[str]:
        """Extract errors from ledger events.

        Args:
            events: List of events from ledger

        Returns:
            List of error messages

        """
        try:
            errors = []

            for event in events:
                try:
                    # Look for TOOL_RESULT events with errors
                    if event.get("event_type") == "TOOL_RESULT":
                        payload = event.get("payload", {})
                        if payload.get("error"):
                            error_msg = payload.get("error", "Unknown error")
                            errors.append(error_msg)
                except Exception as e:
                    logger.warning(f"Error extracting error from event: {e}")

            logger.info(f"Extracted {len(errors)} errors from {len(events)} events")
            return errors

        except Exception as e:
            logger.error(f"Error extracting errors: {e}")
            return []

    @staticmethod
    def get_session_events(session_id: UUID) -> ExecutionData:
        """Get all execution data for a session from ledger.

        Args:
            session_id: Session ID to query

        Returns:
            ExecutionData with all events from session

        """
        try:
            # Query all events for session
            events = LedgerQueryInterface.query_events_for_session(
                session_id=session_id,
                limit=10000,
            )

            # Extract tool calls and errors
            tool_calls = LedgerQueryInterface.extract_tool_calls_from_events(events)
            errors = LedgerQueryInterface.extract_errors_from_events(events)

            # Calculate metrics
            metrics = LedgerQueryInterface.calculate_metrics(tool_calls, errors)

            execution_data = ExecutionData(
                session_id=session_id,
                tool_calls=tool_calls,
                errors=errors,
                metrics=metrics,
            )

            logger.info(
                f"Retrieved execution data for session {session_id}: "
                f"{len(tool_calls)} tool calls, {len(errors)} errors",
            )
            return execution_data

        except Exception as e:
            logger.error(f"Error getting session events: {e}")
            return ExecutionData(
                session_id=session_id,
                tool_calls=[],
                errors=[],
                metrics=ExecutionMetrics(0, 0, 0, 0.0, 0.0),
            )

    @staticmethod
    def calculate_metrics(tool_calls: list[ToolCall], errors: list[str]) -> ExecutionMetrics:
        """Calculate execution metrics from tool calls and errors.

        Args:
            tool_calls: List of tool calls
            errors: List of errors

        Returns:
            ExecutionMetrics

        """
        try:
            # Count unique files accessed
            files_accessed = set()
            for tool_call in tool_calls:
                if "path" in tool_call.input:
                    files_accessed.add(tool_call.input["path"])
                elif "file" in tool_call.input:
                    files_accessed.add(tool_call.input["file"])

            actual_files = len(files_accessed)
            actual_tool_calls = len(tool_calls)
            actual_errors = len(errors)

            # Calculate success rate
            success_rate = 0.0
            if actual_tool_calls > 0:
                success_rate = (actual_tool_calls - actual_errors) / actual_tool_calls

            # Calculate time from first and last event
            actual_time_minutes = 0.0
            if tool_calls and len(tool_calls) > 1:
                try:
                    from datetime import datetime

                    first_time = datetime.fromisoformat(tool_calls[0].timestamp)
                    last_time = datetime.fromisoformat(tool_calls[-1].timestamp)
                    duration = (last_time - first_time).total_seconds() / 60.0
                    actual_time_minutes = max(0.0, duration)
                except Exception as e:
                    logger.warning(f"Error calculating time from events: {e}")

            metrics = ExecutionMetrics(
                actual_files=actual_files,
                actual_tool_calls=actual_tool_calls,
                actual_errors=actual_errors,
                actual_time_minutes=actual_time_minutes,
                success_rate=success_rate,
            )

            logger.info(
                f"Calculated metrics: {actual_files} files, {actual_tool_calls} calls, "
                f"{actual_errors} errors, {success_rate:.2%} success rate",
            )
            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return ExecutionMetrics(0, 0, 0, 0.0, 0.0)
