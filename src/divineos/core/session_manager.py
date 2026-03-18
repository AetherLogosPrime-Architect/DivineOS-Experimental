"""
Session Manager Module — Manages session lifecycle and persistence.

This module provides functions to manage the session lifecycle:
- Initialize sessions and generate/retrieve session IDs
- Persist session IDs to files and environment variables
- End sessions and emit SESSION_END events
- Clear session state

All session operations are marked as internal to prevent recursive capture.

Requirements:
- Requirement 8.1: Generate unique session_id
- Requirement 8.2: Persist session_id to file
- Requirement 8.3: Set session_id as environment variable
- Requirement 8.4: Check environment variable for existing session_id
- Requirement 8.5: Check persistent file for existing session_id
- Requirement 8.6: Reuse session_id for all events in session
- Requirement 8.7: Clear persistent session_id file on session end
- Requirement 8.8: Clear environment variable on session end
"""

import os
import uuid
from pathlib import Path
from typing import Optional
from loguru import logger

from divineos.core.loop_prevention import mark_internal_operation


# Global session state
_current_session_id: Optional[str] = None
_session_start_time: Optional[float] = None


def _get_session_file_path() -> Path:
    """Get the path to the persistent session file."""
    return Path.home() / ".divineos" / "current_session.txt"


def _read_session_file() -> Optional[str]:
    """
    Read session_id from persistent file.

    Returns:
        Optional[str]: Session ID if file exists and is readable, None otherwise
    """
    with mark_internal_operation():
        session_file = _get_session_file_path()
        if session_file.exists():
            try:
                content = session_file.read_text().strip()
                if content:
                    logger.debug(f"Read session_id from file: {content}")
                    return content
            except Exception as e:
                logger.warning(f"Failed to read session file: {e}")
        return None


def _write_session_file(session_id: str) -> bool:
    """
    Write session_id to persistent file.

    Args:
        session_id: Session ID to persist

    Returns:
        bool: True if successful, False otherwise
    """
    with mark_internal_operation():
        session_file = _get_session_file_path()
        try:
            session_file.parent.mkdir(parents=True, exist_ok=True)
            session_file.write_text(session_id)
            logger.debug(f"Wrote session_id to file: {session_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to write session file: {e}")
            return False


def _clear_session_file() -> bool:
    """
    Clear the persistent session file.

    Returns:
        bool: True if successful, False otherwise
    """
    with mark_internal_operation():
        session_file = _get_session_file_path()
        try:
            if session_file.exists():
                session_file.unlink()
                logger.debug("Cleared session file")
            return True
        except Exception as e:
            logger.warning(f"Failed to clear session file: {e}")
            return False


def initialize_session() -> str:
    """
    Initialize a new session or retrieve an existing one.

    This function:
    1. Checks environment variable for existing session_id
    2. Checks persistent file for existing session_id
    3. Generates new session_id if neither exists
    4. Persists session_id to file and environment variable

    Returns:
        str: The session ID to use for this session

    Requirements:
        - Requirement 8.1: Generate unique session_id
        - Requirement 8.2: Persist session_id to file
        - Requirement 8.3: Set session_id as environment variable
        - Requirement 8.4: Check environment variable for existing session_id
        - Requirement 8.5: Check persistent file for existing session_id
    """
    global _current_session_id, _session_start_time

    with mark_internal_operation():
        # Check environment variable first
        env_session_id = os.environ.get("DIVINEOS_SESSION_ID")
        if env_session_id:
            logger.debug(f"Using session_id from environment: {env_session_id}")
            _current_session_id = env_session_id
            return env_session_id

        # Check persistent file
        file_session_id = _read_session_file()
        if file_session_id:
            logger.debug(f"Using session_id from file: {file_session_id}")
            os.environ["DIVINEOS_SESSION_ID"] = file_session_id
            _current_session_id = file_session_id
            return file_session_id

        # Generate new session_id
        new_session_id = str(uuid.uuid4())
        logger.debug(f"Generated new session_id: {new_session_id}")

        # Persist to file
        _write_session_file(new_session_id)

        # Set environment variable
        os.environ["DIVINEOS_SESSION_ID"] = new_session_id

        # Store in global state
        _current_session_id = new_session_id
        import time

        _session_start_time = time.time()

        return new_session_id


def get_current_session_id() -> str:
    """
    Get the current session_id.

    Returns:
        str: The current session ID

    Raises:
        RuntimeError: If no session is active

    Requirements:
        - Requirement 8.6: Reuse session_id for all events in session
    """
    with mark_internal_operation():
        global _current_session_id

        # Try to get from global state first
        if _current_session_id:
            return _current_session_id

        # Try to get from environment
        env_session_id = os.environ.get("DIVINEOS_SESSION_ID")
        if env_session_id:
            _current_session_id = env_session_id
            return env_session_id

        # Try to get from file
        file_session_id = _read_session_file()
        if file_session_id:
            _current_session_id = file_session_id
            os.environ["DIVINEOS_SESSION_ID"] = file_session_id
            return file_session_id

        # No session found
        raise RuntimeError("No active session. Call initialize_session() first.")


def is_session_active() -> bool:
    """
    Check if a session is currently active.

    Returns:
        bool: True if session is active, False otherwise

    Requirements:
        - Requirement 8.6: Check if session_id exists
    """
    with mark_internal_operation():
        try:
            get_current_session_id()
            return True
        except RuntimeError:
            return False


def end_session() -> str:
    """
    End the current session and emit SESSION_END event.

    This function:
    1. Queries ledger for event counts
    2. Calculates session duration
    3. Emits SESSION_END event
    4. Clears session state

    Returns:
        str: The event_id of the SESSION_END event

    Requirements:
        - Requirement 4.1: Create SESSION_END event
        - Requirement 4.2: Emit SESSION_END event
        - Requirement 8.7: Clear persistent session_id file
        - Requirement 8.8: Clear environment variable
    """
    with mark_internal_operation():
        from divineos.event.event_emission import emit_session_end

        try:
            session_id = get_current_session_id()
            logger.debug(f"Ending session: {session_id}")

            # Emit SESSION_END event
            event_id = emit_session_end(session_id=session_id)

            # Clear session state
            clear_session()

            logger.debug(f"Session ended: {session_id}")
            return event_id

        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            # Still try to clear session state
            clear_session()
            raise


def clear_session() -> None:
    """
    Clear the current session state.

    This function:
    1. Clears the persistent session file
    2. Clears the environment variable
    3. Clears the global session state

    Requirements:
        - Requirement 8.7: Clear persistent session_id file
        - Requirement 8.8: Clear environment variable
    """
    global _current_session_id, _session_start_time

    with mark_internal_operation():
        # Clear persistent file
        _clear_session_file()

        # Clear environment variable
        if "DIVINEOS_SESSION_ID" in os.environ:
            del os.environ["DIVINEOS_SESSION_ID"]
            logger.debug("Cleared DIVINEOS_SESSION_ID environment variable")

        # Clear global state
        _current_session_id = None
        _session_start_time = None

        logger.debug("Cleared session state")


def get_session_duration() -> float:
    """
    Get the duration of the current session in seconds.

    Returns:
        float: Duration in seconds, or 0.0 if session not started

    Requirements:
        - Requirement 4.7: Calculate session duration
    """
    with mark_internal_operation():
        import time

        if _session_start_time is None:
            return 0.0

        return time.time() - _session_start_time
