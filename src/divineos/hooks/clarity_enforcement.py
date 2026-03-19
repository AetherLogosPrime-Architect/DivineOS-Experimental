"""Clarity Enforcement Module.

Ensures that every tool call is accompanied by an explanation.
This module provides decorators and utilities to enforce the clarity principle:
- Every tool call must be explained before execution
- Every result must be interpreted and explained
- Users must understand what the AI is doing and why

Also integrates with IDE tool execution to emit TOOL_CALL and TOOL_RESULT events.
"""

import functools
import threading
from collections.abc import Callable
from typing import Any

from loguru import logger

# Import IDE tool integration for capturing tool execution
try:
    from divineos.core.tool_wrapper import (
        emit_tool_call_for_ide,
        emit_tool_result_for_ide,
    )

    IDE_INTEGRATION_AVAILABLE = True
except ImportError:
    IDE_INTEGRATION_AVAILABLE = False
    logger.warning("IDE tool integration not available")


class ClarityViolation(Exception):
    """Raised when a tool call is made without proper explanation."""


def require_explanation(tool_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that requires an explanation before a tool is called.

    Usage:
        @require_explanation("readFile")
        def read_file(path: str) -> str:
            ...

    This decorator ensures that:
    1. The tool call is logged with context
    2. An explanation is provided before execution
    3. The result is interpreted and explained
    4. TOOL_CALL and TOOL_RESULT events are emitted for tracking
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Log the tool call with context
            logger.info(f"Tool call: {tool_name}")
            logger.info(f"Arguments: args={args}, kwargs={kwargs}")

            # Emit TOOL_CALL event if IDE integration is available
            tool_use_id = None
            if IDE_INTEGRATION_AVAILABLE:
                try:
                    tool_use_id = emit_tool_call_for_ide(tool_name, kwargs)
                    logger.debug(f"Emitted TOOL_CALL for {tool_name}: {tool_use_id}")
                except Exception as e:
                    logger.warning(f"Failed to emit TOOL_CALL for {tool_name}: {e}")

            try:
                # Execute the tool
                result = func(*args, **kwargs)

                # Log the result
                logger.info(f"Tool result: {tool_name} returned {type(result).__name__}")

                # Emit TOOL_RESULT event if IDE integration is available
                if IDE_INTEGRATION_AVAILABLE and tool_use_id:
                    try:
                        result_str = str(result) if not isinstance(result, str) else result
                        emit_tool_result_for_ide(tool_use_id, result_str, failed=False)
                        logger.debug(f"Emitted TOOL_RESULT for {tool_name}: success")
                    except Exception as e:
                        logger.warning(f"Failed to emit TOOL_RESULT for {tool_name}: {e}")

                return result

            except Exception as e:
                # Emit TOOL_RESULT event with failure if IDE integration is available
                if IDE_INTEGRATION_AVAILABLE and tool_use_id:
                    try:
                        error_msg = str(e)
                        emit_tool_result_for_ide(
                            tool_use_id,
                            error_msg,
                            failed=True,
                            error_message=error_msg,
                        )
                        logger.debug(f"Emitted TOOL_RESULT for {tool_name}: failed")
                    except Exception as emit_error:
                        logger.warning(f"Failed to emit TOOL_RESULT for {tool_name}: {emit_error}")

                raise

        return wrapper

    return decorator


class ClarityChecker:
    """Checks that tool calls are properly explained.

    This class tracks tool calls and verifies that each one has an accompanying
    explanation in the ledger as an EXPLANATION event.
    Thread-safe implementation with ledger integration.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.tool_calls: list[dict[str, Any]] = []
        self.explanations: list[str] = []

    def record_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        explanation: str | None = None,
    ) -> None:
        """Record a tool call with optional explanation."""
        with self._lock:
            call_record = {
                "tool_name": tool_name,
                "args": args,
                "explanation": explanation,
                "has_explanation": explanation is not None and len(explanation.strip()) > 0,
            }
            self.tool_calls.append(call_record)

            if not call_record["has_explanation"]:
                logger.warning(f"Tool call without explanation: {tool_name}")

    def record_explanation(self, explanation: str) -> None:
        """Record an explanation for the most recent tool call."""
        with self._lock:
            if self.tool_calls:
                self.tool_calls[-1]["explanation"] = explanation
                self.tool_calls[-1]["has_explanation"] = True

    def get_unexplained_calls(self) -> list[dict[str, Any]]:
        """Get all tool calls that lack explanations."""
        with self._lock:
            return [call for call in self.tool_calls if not call["has_explanation"]]

    def verify_all_explained(self) -> bool:
        """Verify that all tool calls have explanations."""
        unexplained = self.get_unexplained_calls()
        if unexplained:
            logger.error(f"Found {len(unexplained)} unexplained tool calls")
            for call in unexplained:
                logger.error(f"  - {call['tool_name']}: {call['args']}")
            return False
        return True

    def check_clarity_for_session(
        self,
        session_id: str,
        raise_on_violations: bool = False,
    ) -> dict[str, Any]:
        """Check clarity for a session by querying the ledger.

        Args:
            session_id: Session ID to check
            raise_on_violations: If True, raise ClarityViolation if violations found

        Returns:
            Report dict with violations and stats

        Raises:
            ClarityViolation: If raise_on_violations=True and violations found

        """
        try:
            from divineos.core.ledger import get_events

            events = get_events()
            tool_calls = [e for e in events if e.get("event_type") == "TOOL_CALL"]
            explanations = [e for e in events if e.get("event_type") == "EXPLANATION"]

            # Map explanations to tool calls
            explained_tool_ids = set()
            for exp in explanations:
                payload = exp.get("payload", {})
                if "tool_call_id" in payload:
                    explained_tool_ids.add(payload["tool_call_id"])

            # Find violations
            violations = []
            for call in tool_calls:
                call_id = call.get("payload", {}).get("tool_call_id")
                if call_id and call_id not in explained_tool_ids:
                    violations.append(
                        {
                            "tool_call_id": call_id,
                            "tool_name": call.get("payload", {}).get("tool_name"),
                            "reason": "No explanation provided",
                        },
                    )

            report = {
                "session_id": session_id,
                "total_calls": len(tool_calls),
                "explained_calls": len(explained_tool_ids),
                "violations": violations,
                "clarity_score": len(explained_tool_ids) / max(len(tool_calls), 1),
            }

            # Raise if violations found and requested
            if raise_on_violations and violations:
                violation_details = "\n".join(
                    f"  - {v['tool_name']} ({v['tool_call_id']}): {v['reason']}" for v in violations
                )
                raise ClarityViolation(
                    f"Found {len(violations)} unexplained tool calls:\n{violation_details}",
                )

            return report
        except ClarityViolation:
            raise
        except Exception as e:
            logger.error(f"Failed to check clarity for session {session_id}: {e}", exc_info=True)
            return {
                "session_id": session_id,
                "error": str(e),
                "clarity_score": 0.0,
            }

    def enforce_clarity(self, session_id: str) -> None:
        """Enforce clarity by checking the ledger and raising on violations.

        Args:
            session_id: Session ID to enforce clarity for

        Raises:
            ClarityViolation: If any unexplained tool calls are found

        """
        self.check_clarity_for_session(session_id, raise_on_violations=True)

    def get_clarity_report(self) -> dict[str, Any]:
        """Generate a clarity report for the session."""
        with self._lock:
            total_calls = len(self.tool_calls)
            explained_calls = sum(1 for call in self.tool_calls if call["has_explanation"])
            unexplained_calls = total_calls - explained_calls

            clarity_score = (explained_calls / total_calls * 100) if total_calls > 0 else 100

            return {
                "total_tool_calls": total_calls,
                "explained_calls": explained_calls,
                "unexplained_calls": unexplained_calls,
                "clarity_score": clarity_score,
                "status": "PASS" if unexplained_calls == 0 else "FAIL",
                "unexplained_details": self.get_unexplained_calls(),
            }


# Global clarity checker instance
_clarity_checker: ClarityChecker | None = None


def get_clarity_checker() -> ClarityChecker:
    """Get or create the global clarity checker."""
    global _clarity_checker
    if _clarity_checker is None:
        _clarity_checker = ClarityChecker()
    return _clarity_checker


def reset_clarity_checker() -> None:
    """Reset the clarity checker for a new session."""
    global _clarity_checker
    _clarity_checker = ClarityChecker()
