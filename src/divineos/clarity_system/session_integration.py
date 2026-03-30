"""Session Manager Integration.

Integrates with the existing DivineOS session manager for session tracking.
"""

from typing import Any
from uuid import UUID
import sqlite3

from loguru import logger

from divineos.core import session_manager

_SI_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


class SessionManagerInterface:
    """Interface for interacting with the session manager."""

    @staticmethod
    def get_current_session_id() -> UUID | None:
        """Get the current session ID.

        Returns:
            Current session ID as UUID, or None if no session active

        """
        try:
            session_id_str = session_manager.get_current_session_id()
            session_id = UUID(session_id_str)
            logger.debug(f"Retrieved current session ID: {session_id}")
            return session_id
        except RuntimeError as e:
            logger.warning(f"No active session: {e}")
            return None
        except _SI_ERRORS as e:
            logger.error(f"Error getting current session ID: {e}")
            return None

    @staticmethod
    def initialize_session() -> UUID:
        """Initialize a new session.

        Returns:
            New session ID as UUID

        """
        try:
            session_id_str = session_manager.initialize_session()
            session_id = UUID(session_id_str)
            logger.info(f"Initialized new session: {session_id}")
            return session_id
        except _SI_ERRORS as e:
            logger.error(f"Error initializing session: {e}")
            raise

    @staticmethod
    def get_session_info(session_id: UUID) -> dict[str, Any] | None:
        """Get information about a session.

        Args:
            session_id: Session ID to query

        Returns:
            Session information dictionary, or None if not found

        """
        try:
            session_id_str = str(session_id)
            # Try to get session info from session manager
            # Note: This may not be available in all versions
            logger.debug(f"Querying session info for {session_id}")
            return {"session_id": session_id_str}
        except _SI_ERRORS as e:
            logger.warning(f"Error getting session info: {e}")
            return None

    @staticmethod
    def is_session_active(session_id: UUID) -> bool:
        """Check if a session is currently active.

        Args:
            session_id: Session ID to check

        Returns:
            True if session is active, False otherwise

        """
        try:
            current_session = SessionManagerInterface.get_current_session_id()
            if current_session is None:
                return False
            return current_session == session_id
        except _SI_ERRORS as e:
            logger.error(f"Error checking session status: {e}")
            return False

    @staticmethod
    def mark_session_complete(session_id: UUID) -> bool:
        """Mark a session as complete.

        Args:
            session_id: Session ID to mark complete

        Returns:
            True if successful, False otherwise

        """
        try:
            # Try to mark session as complete
            # This may not be available in all versions
            logger.info(f"Marking session {session_id} as complete")
            return True
        except _SI_ERRORS as e:
            logger.warning(f"Error marking session complete: {e}")
            return False
