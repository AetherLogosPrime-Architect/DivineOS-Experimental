"""MCP Integration Layer for Agent Tool Capture.

Intercepts agent tool calls at the MCP protocol layer and automatically
emits TOOL_CALL and TOOL_RESULT events for all agent operations.

This layer is the core of the agent integration system, ensuring all agent
tool invocations are captured transparently without requiring code changes.
"""

import time
import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any
import sqlite3

from loguru import logger

from divineos.core.error_handling import (
    EventCaptureError,
    SessionError,
    handle_error,
)
from divineos.core.loop_prevention import (
    mark_internal_operation,
    should_capture_tool,
)
from divineos.core.session_manager import get_current_session_id
from divineos.event.event_emission import emit_explanation, emit_tool_call, emit_tool_result

_MI_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


def validate_explanation(tool_input: dict[str, Any]) -> bool:
    """Validate that tool_input contains a non-empty explanation.

    Args:
        tool_input: Tool input parameters

    Returns:
        True if explanation is valid, False otherwise

    """
    if not isinstance(tool_input, dict):
        return False

    explanation = tool_input.get("explanation", "")
    if not isinstance(explanation, str):
        return False

    # Check if explanation is not empty or whitespace-only
    return bool(explanation.strip())


def emit_agent_tool_call(
    tool_name: str,
    tool_input: dict[str, Any],
    session_id: str,
    tool_use_id: str | None = None,
) -> str:
    """Emit a TOOL_CALL event for agent tool invocation.

    Args:
        tool_name: Name of the tool being called
        tool_input: Input parameters for the tool
        session_id: Current session ID
        tool_use_id: Optional unique tool use ID (generated if not provided)

    Returns:
        Event ID of the emitted TOOL_CALL event

    Raises:
        ValueError: If explanation is missing or invalid

    """
    if tool_use_id is None:
        tool_use_id = str(uuid.uuid4())

    # Validate explanation
    if not validate_explanation(tool_input):
        logger.warning(
            f"Tool call '{tool_name}' missing or invalid explanation. "
            f"Explanation is required for clarity enforcement.",
        )
        # Emit explanation warning event
        try:
            with mark_internal_operation():
                emit_explanation(
                    explanation_text=f"Tool '{tool_name}' called without proper explanation",
                    session_id=session_id,
                )
        except EventCaptureError as e:
            handle_error(e, "emit_explanation_warning", {"tool_name": tool_name})
        except _MI_ERRORS as e:
            handle_error(e, "emit_explanation_warning", {"tool_name": tool_name})

    # Create TOOL_CALL event
    try:
        with mark_internal_operation():
            event_id = emit_tool_call(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_use_id=tool_use_id,
                session_id=session_id,
            )
        logger.debug(
            f"Emitted TOOL_CALL: {tool_name} (tool_use_id={tool_use_id[:8]}..., "
            f"event_id={event_id[:8]}...)",
        )
        return event_id
    except EventCaptureError as e:
        handle_error(
            e,
            "emit_agent_tool_call",
            {"tool_name": tool_name, "tool_use_id": tool_use_id},
        )
        raise
    except _MI_ERRORS as e:
        handle_error(
            e,
            "emit_agent_tool_call",
            {"tool_name": tool_name, "tool_use_id": tool_use_id},
        )
        raise


def emit_agent_tool_result(
    tool_name: str,
    tool_use_id: str,
    result: Any,
    duration_ms: int,
    session_id: str,
    failed: bool = False,
    error_message: str | None = None,
) -> str:
    """Emit a TOOL_RESULT event for agent tool execution result.

    Args:
        tool_name: Name of the tool
        tool_use_id: Unique tool use ID (matches TOOL_CALL)
        result: Result from tool execution
        duration_ms: Execution duration in milliseconds
        session_id: Current session ID
        failed: Whether tool execution failed
        error_message: Error message if failed

    Returns:
        Event ID of the emitted TOOL_RESULT event

    """
    # Convert result to string
    if result is None:
        result_str = ""
    elif isinstance(result, str):
        result_str = result
    else:
        result_str = str(result)

    # Truncate very large results
    if len(result_str) > 10000:
        result_str = result_str[:10000] + "\n... [truncated]"

    try:
        with mark_internal_operation():
            event_id = emit_tool_result(
                tool_name=tool_name,
                tool_use_id=tool_use_id,
                result=result_str,
                duration_ms=duration_ms,
                failed=failed,
                error_message=error_message,
                session_id=session_id,
            )
        logger.debug(
            f"Emitted TOOL_RESULT: {tool_name} (tool_use_id={tool_use_id[:8]}..., "
            f"duration={duration_ms}ms, failed={failed}, event_id={event_id[:8]}...)",
        )
        return event_id
    except EventCaptureError as e:
        handle_error(
            e,
            "emit_agent_tool_result",
            {"tool_name": tool_name, "tool_use_id": tool_use_id},
        )
        raise
    except _MI_ERRORS as e:
        handle_error(
            e,
            "emit_agent_tool_result",
            {"tool_name": tool_name, "tool_use_id": tool_use_id},
        )
        raise


def create_tool_interceptor(
    tool_name: str, original_tool: Callable[..., Any]
) -> Callable[..., Any]:
    """Create an interceptor wrapper for a tool that captures events.

    Args:
        tool_name: Name of the tool
        original_tool: Original tool function

    Returns:
        Wrapped tool function that captures events

    The wrapper:
    1. Checks if tool should be captured
    2. Validates explanation parameter
    3. Emits TOOL_CALL event
    4. Measures execution time
    5. Executes the tool
    6. Emits TOOL_RESULT event
    7. Returns result or re-raises exception

    """

    @wraps(original_tool)
    def wrapped_tool(*args: Any, **kwargs: Any) -> Any:
        # Check if tool should be captured
        if not should_capture_tool(tool_name):
            logger.debug(f"Skipping capture for internal tool: {tool_name}")
            return original_tool(*args, **kwargs)

        # Get session ID
        try:
            session_id = get_current_session_id()
        except SessionError as e:
            handle_error(e, "get_current_session_id_in_wrapper", {"tool_name": tool_name})
            # Continue without capture if session ID unavailable
            return original_tool(*args, **kwargs)
        except _MI_ERRORS as e:
            handle_error(e, "get_current_session_id_in_wrapper", {"tool_name": tool_name})
            # Continue without capture if session ID unavailable
            return original_tool(*args, **kwargs)

        # Extract tool_input from kwargs (standard for MCP tools)
        tool_input = kwargs.copy()
        tool_use_id = str(uuid.uuid4())

        # Emit TOOL_CALL
        try:
            emit_agent_tool_call(
                tool_name=tool_name,
                tool_input=tool_input,
                session_id=session_id,
                tool_use_id=tool_use_id,
            )
        except EventCaptureError as e:
            handle_error(e, "emit_tool_call_in_wrapper", {"tool_name": tool_name})
            # Continue execution even if event capture fails
        except _MI_ERRORS as e:
            handle_error(e, "emit_tool_call_in_wrapper", {"tool_name": tool_name})
            # Continue execution even if event capture fails

        # Measure execution time
        start_time = time.perf_counter()
        try:
            result = original_tool(*args, **kwargs)
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Emit TOOL_RESULT
            try:
                emit_agent_tool_result(
                    tool_name=tool_name,
                    tool_use_id=tool_use_id,
                    result=result,
                    duration_ms=duration_ms,
                    session_id=session_id,
                    failed=False,
                    error_message=None,
                )
            except EventCaptureError as e:
                handle_error(e, "emit_tool_result_in_wrapper", {"tool_name": tool_name})
            except _MI_ERRORS as e:
                handle_error(e, "emit_tool_result_in_wrapper", {"tool_name": tool_name})

            return result

        except _MI_ERRORS as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Emit TOOL_RESULT with error
            try:
                emit_agent_tool_result(
                    tool_name=tool_name,
                    tool_use_id=tool_use_id,
                    result=None,
                    duration_ms=duration_ms,
                    session_id=session_id,
                    failed=True,
                    error_message=str(e),
                )
            except EventCaptureError as emit_error:
                handle_error(
                    emit_error,
                    "emit_error_tool_result_in_wrapper",
                    {"tool_name": tool_name},
                )
            except Exception as emit_error:
                handle_error(
                    emit_error,
                    "emit_error_tool_result_in_wrapper",
                    {"tool_name": tool_name},
                )

            # Re-raise the original exception
            raise

    return wrapped_tool


def setup_mcp_agent_integration() -> None:
    """Initialize MCP integration for agent tool capture.

    This function sets up the MCP protocol layer to intercept all agent
    tool calls and automatically emit TOOL_CALL and TOOL_RESULT events.

    This is called once at system startup to enable agent self-observation.
    """
    logger.info("Setting up MCP agent integration...")

    try:
        # Initialize loop prevention
        from divineos.core.loop_prevention import initialize_loop_prevention

        initialize_loop_prevention()
        logger.info("Loop prevention initialized")

        # Log successful setup
        logger.info("MCP agent integration setup complete")

    except _MI_ERRORS as e:
        handle_error(e, "setup_mcp_agent_integration")
        raise


def shutdown_mcp_agent_integration() -> None:
    """Shutdown MCP integration for agent tool capture.

    This function cleans up resources used by the MCP integration layer.
    """
    logger.info("Shutting down MCP agent integration...")

    try:
        # Cleanup loop prevention
        from divineos.core.loop_prevention import shutdown_loop_prevention

        shutdown_loop_prevention()
        logger.info("Loop prevention shutdown complete")

        logger.info("MCP agent integration shutdown complete")

    except _MI_ERRORS as e:
        handle_error(e, "shutdown_mcp_agent_integration")
