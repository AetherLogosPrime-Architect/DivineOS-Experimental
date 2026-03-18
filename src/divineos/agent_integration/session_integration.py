"""
Session Integration for Agent Operations

Integrates agent operations with the session management system,
ensuring all agent tool calls are tracked within the current session.
"""

import os

from divineos.agent_integration.logging_config import logger
from divineos.core.session_manager import (
    get_current_session_id as get_session_id,
    get_session_metadata,
    update_session_metadata,
)


def get_agent_session_id() -> str:
    """
    Get the current session ID for agent operations.

    Attempts to retrieve session ID from:
    1. Environment variable KIRO_SESSION_ID
    2. Session manager
    3. Creates new session if needed

    Returns:
        Current session ID

    Raises:
        RuntimeError: If session ID cannot be retrieved or created
    """
    # Check environment variable first
    env_session_id = os.environ.get("KIRO_SESSION_ID")
    if env_session_id:
        logger.debug(f"Using session ID from environment: {env_session_id[:8]}...")
        return env_session_id

    # Try to get from session manager
    try:
        session_id = get_session_id()
        logger.debug(f"Using session ID from session manager: {session_id[:8]}...")
        return session_id
    except Exception as e:
        logger.error(f"Failed to get session ID from session manager: {e}")
        raise RuntimeError(f"Cannot retrieve session ID: {e}")


def track_agent_tool_call(session_id: str) -> None:
    """
    Track an agent tool call in the session metadata.

    Args:
        session_id: Current session ID
    """
    try:
        metadata = get_session_metadata(session_id)
        if metadata is None:
            metadata = {}

        # Increment agent tool call count
        agent_tool_calls = metadata.get("agent_tool_calls", 0)
        metadata["agent_tool_calls"] = agent_tool_calls + 1

        # Update metadata
        update_session_metadata(session_id, metadata)
        logger.debug(f"Tracked agent tool call (total: {metadata['agent_tool_calls']})")

    except Exception as e:
        logger.error(f"Failed to track agent tool call: {e}")
        # Continue even if tracking fails


def track_agent_tool_result(session_id: str, failed: bool = False) -> None:
    """
    Track an agent tool result in the session metadata.

    Args:
        session_id: Current session ID
        failed: Whether the tool execution failed
    """
    try:
        metadata = get_session_metadata(session_id)
        if metadata is None:
            metadata = {}

        # Increment agent tool result count
        agent_tool_results = metadata.get("agent_tool_results", 0)
        metadata["agent_tool_results"] = agent_tool_results + 1

        # Track failures
        if failed:
            agent_tool_failures = metadata.get("agent_tool_failures", 0)
            metadata["agent_tool_failures"] = agent_tool_failures + 1

        # Update metadata
        update_session_metadata(session_id, metadata)
        logger.debug(
            f"Tracked agent tool result (total: {metadata['agent_tool_results']}, "
            f"failures: {metadata.get('agent_tool_failures', 0)})"
        )

    except Exception as e:
        logger.error(f"Failed to track agent tool result: {e}")
        # Continue even if tracking fails


def get_session_agent_stats(session_id: str) -> dict:
    """
    Get agent operation statistics for a session.

    Args:
        session_id: Session ID

    Returns:
        Dictionary with agent operation statistics
    """
    try:
        metadata = get_session_metadata(session_id)
        if metadata is None:
            metadata = {}

        return {
            "agent_tool_calls": metadata.get("agent_tool_calls", 0),
            "agent_tool_results": metadata.get("agent_tool_results", 0),
            "agent_tool_failures": metadata.get("agent_tool_failures", 0),
        }

    except Exception as e:
        logger.error(f"Failed to get session agent stats: {e}")
        return {
            "agent_tool_calls": 0,
            "agent_tool_results": 0,
            "agent_tool_failures": 0,
        }
