"""Session Manager Module — Manages session lifecycle and persistence.

This module provides functions to manage the session lifecycle:
- Initialize sessions and generate/retrieve session IDs
- Persist session IDs to files and environment variables
- End sessions and emit CONSOLIDATION_CHECKPOINT events (formerly SESSION_END)
- Clear session state
- Track session duration
- Provide session tracker for backward compatibility

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
import sqlite3
import time
import uuid
from pathlib import Path

from loguru import logger

from divineos.core.loop_prevention import mark_internal_operation

# Global session state
_current_session_id: str | None = None
_session_start_time: float | None = None


def _get_session_file_path() -> Path:
    """Get the path to the persistent session file."""
    return Path.home() / ".divineos" / "current_session.txt"


def _read_session_file() -> str | None:
    """Read session_id from persistent file.

    Error Handling:
    - Catches file read errors
    - Catches permission errors
    - Logs warnings without crashing
    - Returns None on any error

    Returns:
        Optional[str]: Session ID if file exists and is readable, None otherwise

    """
    with mark_internal_operation():
        session_file = _get_session_file_path()
        if session_file.exists():
            try:
                content = session_file.read_text(encoding="utf-8").strip()
                if content:
                    logger.debug(f"Read session_id from file: {content}")
                    return content
            except PermissionError as e:
                logger.warning(f"Permission denied reading session file: {e}")
            except FileNotFoundError as e:
                logger.warning(f"Session file not found: {e}")
            except _SM_ERRORS as e:
                logger.warning(f"Failed to read session file: {e}", exc_info=True)
        return None


def _write_session_file(session_id: str) -> bool:
    """Write session_id to persistent file.

    Error Handling:
    - Catches directory creation errors
    - Catches file write errors
    - Catches permission errors
    - Logs warnings without crashing
    - Returns False on any error

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
        except PermissionError as e:
            logger.warning(f"Permission denied writing session file: {e}")
            return False
        except OSError as e:
            logger.warning(f"OS error writing session file: {e}")
            return False
        except _SM_ERRORS as e:
            logger.warning(f"Failed to write session file: {e}", exc_info=True)
            return False


def _clear_session_file() -> bool:
    """Clear the persistent session file.

    Error Handling:
    - Catches file deletion errors
    - Catches permission errors
    - Logs warnings without crashing
    - Returns True even if file doesn't exist

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
        except PermissionError as e:
            logger.warning(f"Permission denied deleting session file: {e}")
            return False
        except FileNotFoundError as e:
            logger.debug(f"Session file already deleted: {e}")
            return True
        except _SM_ERRORS as e:
            logger.warning(f"Failed to clear session file: {e}", exc_info=True)
            return False


def initialize_session() -> str:
    """Initialize a new session or retrieve an existing one.

    This function:
    1. Checks environment variable for existing session_id
    2. Checks persistent file for existing session_id
    3. Generates new session_id if neither exists
    4. Persists session_id to file and environment variable

    Error Handling:
    - Catches file read/write errors
    - Generates new session_id on persistence failure
    - Logs errors without crashing
    - Always returns a valid session_id

    Returns:
        str: The session ID to use for this session

    Requirements:
        - Requirement 8.1: Generate unique session_id
        - Requirement 8.2: Persist session_id to file
        - Requirement 8.3: Set session_id as environment variable
        - Requirement 8.4: Check environment variable for existing session_id
        - Requirement 8.5: Check persistent file for existing session_id
        - Requirement 10.1-10.6: Handle errors gracefully

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

        # Persist to file (with error handling)
        if not _write_session_file(new_session_id):
            logger.warning(
                "Failed to persist session_id to file, continuing with in-memory session",
            )

        # Set environment variable
        try:
            os.environ["DIVINEOS_SESSION_ID"] = new_session_id
        except _SM_ERRORS as e:
            logger.warning(f"Failed to set environment variable: {e}")

        # Store in global state
        _current_session_id = new_session_id
        _session_start_time = time.time()

        return new_session_id


def get_current_session_id() -> str:
    """Get the current session_id.

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
        msg = "No active session. Call initialize_session() first."
        raise RuntimeError(msg)


def is_session_active() -> bool:
    """Check if a session is currently active.

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
    """End the current session and emit SESSION_END event.

    This function:
    1. Queries ledger for event counts
    2. Calculates session duration
    3. Emits SESSION_END event
    4. Clears session state

    Error Handling:
    - Catches SESSION_END event emission errors
    - Attempts to clear session state even if SESSION_END fails
    - Logs errors without crashing
    - Returns event_id if successful, empty string on error

    Returns:
        str: The event_id of the SESSION_END event

    Requirements:
        - Requirement 4.1: Create SESSION_END event
        - Requirement 4.2: Emit SESSION_END event
        - Requirement 8.7: Clear persistent session_id file
        - Requirement 8.8: Clear environment variable
        - Requirement 10.1-10.6: Handle errors gracefully

    """
    with mark_internal_operation():
        from divineos.event.event_emission import emit_consolidation_checkpoint

        try:
            session_id = get_current_session_id()
            logger.debug(f"Ending session: {session_id}")

            # Emit CONSOLIDATION_CHECKPOINT event with error handling
            event_id = ""
            try:
                event_id = emit_consolidation_checkpoint(session_id=session_id)
                logger.debug(f"CONSOLIDATION_CHECKPOINT event emitted: {event_id}")
            except ValueError as e:
                logger.error(
                    f"Validation error during CONSOLIDATION_CHECKPOINT event emission: {e}"
                )
                logger.warning("Continuing with session cleanup")
            except _SM_ERRORS as e:
                logger.error(f"Failed to emit CONSOLIDATION_CHECKPOINT event: {e}", exc_info=True)
                logger.warning("Continuing with session cleanup")

            # Clear session state (always attempt this)
            clear_session()

            logger.debug(f"Session ended: {session_id}")
            return event_id

        except _SM_ERRORS as e:
            logger.error(f"Unexpected error during session end: {e}", exc_info=True)
            # Still try to clear session state
            try:
                clear_session()
            except _SM_ERRORS as e2:
                logger.error(f"Failed to clear session state: {e2}")
            raise


def clear_session() -> None:
    """Clear the current session state.

    This function:
    1. Clears the persistent session file
    2. Clears the environment variable
    3. Clears the global session state

    Error Handling:
    - Catches file deletion errors
    - Catches environment variable errors
    - Logs warnings without crashing
    - Attempts to clear all state even if some operations fail

    Requirements:
        - Requirement 8.7: Clear persistent session_id file
        - Requirement 8.8: Clear environment variable
        - Requirement 10.1-10.6: Handle errors gracefully
    """
    global _current_session_id, _session_start_time

    with mark_internal_operation():
        # Clear persistent file
        try:
            _clear_session_file()
        except _SM_ERRORS as e:
            logger.warning(f"Error clearing session file: {e}")

        # Clear environment variable
        try:
            if "DIVINEOS_SESSION_ID" in os.environ:
                del os.environ["DIVINEOS_SESSION_ID"]
                logger.debug("Cleared DIVINEOS_SESSION_ID environment variable")
        except _SM_ERRORS as e:
            logger.warning(f"Error clearing environment variable: {e}")

        # Clear global state
        _current_session_id = None
        _session_start_time = None

        logger.debug("Cleared session state")


def get_session_duration() -> float:
    """Get the duration of the current session in seconds.

    Returns:
        float: Duration in seconds, or 0.0 if session not started

    Requirements:
        - Requirement 4.7: Calculate session duration

    """
    with mark_internal_operation():
        if _session_start_time is None:
            return 0.0

        return time.time() - _session_start_time


class SessionTracker:
    """Manages session ID generation and tracking (backward compatibility wrapper)."""

    def __init__(self) -> None:
        """Initialize session tracker."""
        # SessionTracker manages in-memory session state only.
        # Persistent session file is managed by get_or_create_session_id() and initialize_session()
        # This avoids race conditions and ensures single source of truth for session persistence.

        # Generate initial session ID (will be overridden by initialize_session if file exists)
        self._current_session_id: str | None = str(uuid.uuid4())
        logger.trace(f"Initialized session tracker with session: {self._current_session_id}")

        # Always initialize start_time
        # This ensures end_session() and get_session_duration() never return None
        self._session_start_time: float | None = time.time()

    def start_session(self) -> str:
        """Start a new session and return the session ID.

        Returns:
            session_id: Unique identifier for the session

        """
        self._current_session_id = str(uuid.uuid4())
        self._session_start_time = time.time()
        logger.debug(f"Started session: {self._current_session_id}")
        return self._current_session_id

    def get_current_session_id(self) -> str:
        """Get the current session ID.

        Returns:
            session_id: Current session ID (always set after __init__)

        """
        # Should never be None after __init__, but handle gracefully
        if self._current_session_id is None:
            logger.warning("Session ID is None, generating new one")
            return self.start_session()
        return self._current_session_id

    def end_session(self) -> str | None:
        """End the current session.

        Returns:
            session_id: The session ID that was ended, or None if no session active

        """
        if self._current_session_id is None:
            return None

        session_id = self._current_session_id
        self._current_session_id = None
        self._session_start_time = None
        logger.debug(f"Ended session: {session_id}")
        return session_id

    def get_session_duration(self) -> float | None:
        """Get the duration of the current session in seconds.

        Returns:
            duration: Duration in seconds, or None if no session active

        """
        if self._session_start_time is None:
            return None
        return time.time() - self._session_start_time


# Global session tracker instance (for backward compatibility)
_session_tracker = SessionTracker()


def get_session_tracker() -> SessionTracker:
    """Get the global session tracker instance.

    This function is provided for backward compatibility with code that imports
    from event_capture.py. New code should use the module-level functions instead.

    Returns:
        SessionTracker: The global session tracker instance

    """
    return _session_tracker


_SM_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


def get_or_create_session_id(session_id: str | None = None) -> str:
    """Get or create a session ID, ensuring consistency across all events in a session.

    This function uses environment variables and persistent files to ensure all events
    in a session share the same session ID. It consolidates session logic from
    event_emission.py into the canonical session manager.

    Args:
        session_id: Optional explicit session ID (if provided, uses this directly)

    Returns:
        str: The session ID to use for the event

    Logic:
        1. If session_id is explicitly provided, use it
        2. If DIVINEOS_SESSION_ID environment variable is set, use that
        3. If persistent file exists and has non-empty content, use that
        4. Otherwise, generate a new session ID and set both env var and file

    Requirements:
        - Requirement 8.1: Generate unique session_id
        - Requirement 8.2: Persist session_id to file
        - Requirement 8.3: Set session_id as environment variable
        - Requirement 8.4: Check environment variable for existing session_id
        - Requirement 8.5: Check persistent file for existing session_id
        - Requirement 8.6: Reuse session_id for all events in session

    """
    with mark_internal_operation():
        # If session_id is explicitly provided, use it directly
        if session_id:
            return session_id

        # Check environment variable first (persists for IDE session)
        env_session_id = os.environ.get("DIVINEOS_SESSION_ID")
        if env_session_id:
            logger.debug(f"Using session_id from environment: {env_session_id}")
            return env_session_id

        session_file = _get_session_file_path()
        session_file.parent.mkdir(parents=True, exist_ok=True)

        # Try to read existing session ID from persistent file
        if session_file.exists():
            try:
                existing_id = session_file.read_text(encoding="utf-8").strip()
                if existing_id:  # Only use if non-empty
                    logger.debug(f"Using existing session_id from file: {existing_id}")
                    # Also set environment variable for this process
                    os.environ["DIVINEOS_SESSION_ID"] = existing_id
                    return existing_id
            except _SM_ERRORS as e:
                logger.warning(f"Failed to read session_id file: {e}")

        # Generate new session ID only if file doesn't exist or is empty
        current_session_id = get_session_tracker().get_current_session_id()
        logger.debug(f"Generated new session_id: {current_session_id}")

        # Write to persistent file
        try:
            session_file.write_text(current_session_id)
            logger.debug(f"Wrote session_id to persistent file: {current_session_id}")
        except _SM_ERRORS as e:
            logger.warning(f"Failed to write session_id file: {e}")

        # Set environment variable for this process
        os.environ["DIVINEOS_SESSION_ID"] = current_session_id

        return current_session_id
