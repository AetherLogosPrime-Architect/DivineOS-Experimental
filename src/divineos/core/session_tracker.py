"""Session Tracker — Backward-compatible OOP wrapper around session state.

Extracted from session_manager.py to keep the module under 500 lines.
The class manages in-memory session state only; persistent file and
environment-variable handling live in session_manager.
"""

import time
import uuid

from loguru import logger


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
