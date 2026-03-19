"""Execution Analyzer.

Queries ledger and extracts actual execution data for comparison.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger

from .base import ExecutionAnalyzer
from .ledger_integration import LedgerQueryInterface
from .types import ExecutionData, ExecutionMetrics, ToolCall


class DefaultExecutionAnalyzer(ExecutionAnalyzer):
    """Default implementation of execution analyzer."""

    def __init__(self, ledger: Any = None) -> None:
        """Initialize the execution analyzer.

        Args:
            ledger: Optional ledger instance for querying events

        """
        self.ledger = ledger

    def validate(self) -> bool:
        """Validate component is properly initialized."""
        return True

    def analyze_execution(self, session_id: UUID) -> ExecutionData:
        """Analyze execution from ledger.

        Args:
            session_id: Session ID to analyze

        Returns:
            Structured execution data

        """
        try:
            # Use ledger integration to get session events
            execution_data = LedgerQueryInterface.get_session_events(session_id)

            logger.info(
                f"Analyzed execution for session {session_id}: "
                f"{len(execution_data.tool_calls)} tool calls, {len(execution_data.errors)} errors",
            )
            return execution_data

        except Exception as e:
            logger.error(f"Error analyzing execution: {e}")
            # Return minimal execution data
            return ExecutionData(
                session_id=session_id,
                tool_calls=[],
                errors=[],
                metrics=ExecutionMetrics(0, 0, 0, 0.0, 0.0),
            )

    def extract_tool_calls(self, session_id: UUID) -> list[ToolCall]:
        """Extract tool calls from ledger for session.

        Args:
            session_id: Session ID to query

        Returns:
            List of tool calls

        """
        try:
            if not self.ledger:
                logger.warning("Ledger not available, returning empty tool calls")
                return []

            # Query ledger for TOOL_CALL events
            events = self.ledger.query_events(
                session_id=session_id,
                event_type="TOOL_CALL",
            )

            tool_calls = []
            for event in events:
                try:
                    tool_call = ToolCall(
                        tool_name=event.payload.get("tool_name", "unknown"),
                        timestamp=event.timestamp,
                        input=event.payload.get("tool_input", {}),
                    )
                    tool_calls.append(tool_call)
                except Exception as e:
                    logger.warning(f"Error extracting tool call from event: {e}")

            logger.info(f"Extracted {len(tool_calls)} tool calls for session {session_id}")
            return tool_calls

        except Exception as e:
            logger.error(f"Error extracting tool calls: {e}")
            return []

    def extract_errors(self, session_id: UUID) -> list[str]:
        """Extract errors from ledger for session.

        Args:
            session_id: Session ID to query

        Returns:
            List of error messages

        """
        try:
            if not self.ledger:
                logger.warning("Ledger not available, returning empty errors")
                return []

            # Query ledger for failed TOOL_RESULT events
            events = self.ledger.query_events(
                session_id=session_id,
                event_type="TOOL_RESULT",
            )

            errors = []
            for event in events:
                try:
                    # Check if result indicates an error
                    if event.payload.get("error"):
                        error_msg = event.payload.get("error", "Unknown error")
                        errors.append(error_msg)
                except Exception as e:
                    logger.warning(f"Error extracting error from event: {e}")

            logger.info(f"Extracted {len(errors)} errors for session {session_id}")
            return errors

        except Exception as e:
            logger.error(f"Error extracting errors: {e}")
            return []

    def calculate_execution_metrics(self, execution_data: ExecutionData) -> ExecutionMetrics:
        """Calculate metrics from execution data.

        Args:
            execution_data: Execution data with tool calls and errors

        Returns:
            Calculated execution metrics

        """
        return self._calculate_metrics_from_data(
            tool_calls=execution_data.tool_calls,
            errors=execution_data.errors,
        )

    def _calculate_metrics_from_data(
        self,
        tool_calls: list[ToolCall],
        errors: list[str],
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> ExecutionMetrics:
        """Calculate metrics from tool calls and errors.

        Args:
            tool_calls: List of tool calls
            errors: List of errors
            start_time: Optional start timestamp
            end_time: Optional end timestamp

        Returns:
            Calculated execution metrics

        """
        try:
            # Count unique files accessed (from tool inputs)
            files_accessed = set()
            for tool_call in tool_calls:
                # Look for file paths in tool inputs
                if "path" in tool_call.input:
                    files_accessed.add(tool_call.input["path"])
                elif "file" in tool_call.input:
                    files_accessed.add(tool_call.input["file"])

            actual_files = len(files_accessed)
            actual_tool_calls = len(tool_calls)
            actual_errors = len(errors)

            # Calculate duration if timestamps provided
            actual_time_minutes = 0.0
            if start_time and end_time:
                try:
                    start = datetime.fromisoformat(start_time)
                    end = datetime.fromisoformat(end_time)
                    duration = (end - start).total_seconds() / 60.0
                    actual_time_minutes = max(0.0, duration)
                except Exception as e:
                    logger.warning(f"Error calculating duration: {e}")

            # Calculate success rate
            success_rate = 0.0
            if actual_tool_calls > 0:
                success_rate = (actual_tool_calls - actual_errors) / actual_tool_calls

            metrics = ExecutionMetrics(
                actual_files=actual_files,
                actual_tool_calls=actual_tool_calls,
                actual_errors=actual_errors,
                actual_time_minutes=actual_time_minutes,
                success_rate=success_rate,
            )

            logger.info(
                f"Calculated execution metrics: "
                f"{actual_files} files, {actual_tool_calls} calls, "
                f"{actual_errors} errors, {success_rate:.2%} success rate",
            )
            return metrics

        except Exception as e:
            logger.error(f"Error calculating execution metrics: {e}")
            return ExecutionMetrics(0, 0, 0, 0.0, 0.0)
