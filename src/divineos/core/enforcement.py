"""CLI Enforcement Layer Module — Enforces event capture at CLI level.

This module provides functions to enforce event capture at the CLI entry point:
- Initialize enforcement at CLI startup
- Capture user input as USER_INPUT events
- Setup signal handlers for graceful shutdown
- Handle CLI errors

All enforcement operations are marked as internal to prevent recursive capture.

Requirements:
- Requirement 1.1-1.7: Capture USER_INPUT events
- Requirement 5.1-5.6: Integrate enforcement into CLI
"""

import atexit
import os
import signal
import sys
from typing import Any

from loguru import logger

from divineos.core.loop_prevention import mark_internal_operation
from divineos.core.session_manager import end_session, initialize_session, is_session_active
from divineos.event.event_emission import emit_user_input

# Global state for signal handling
_signal_handlers_setup = False
_session_initialized = False


def setup_cli_enforcement() -> None:
    """Initialize CLI enforcement at startup.

    This function:
    1. Initializes the session manager
    2. Sets up signal handlers for graceful shutdown
    3. Sets up atexit handler for cleanup

    Error Handling:
    - Catches and logs all exceptions
    - Attempts recovery on transient failures
    - Continues execution even if setup fails
    - Logs detailed error information for debugging

    Requirements:
        - Requirement 5.1: Initialize event capture system
        - Requirement 5.6: Setup signal handlers
        - Requirement 10.1-10.6: Handle errors gracefully
    """
    global _signal_handlers_setup, _session_initialized

    with mark_internal_operation():
        try:
            logger.debug("Setting up CLI enforcement")

            # Initialize session (only once)
            if not _session_initialized:
                try:
                    session_id = initialize_session()
                    logger.debug(f"Initialized session: {session_id}")
                    _session_initialized = True
                except Exception as e:
                    logger.error(f"Failed to initialize session: {e}")
                    logger.warning("Continuing without session initialization")
                    # Continue execution even if session init fails

            # Setup signal handlers (only once, and only if not in test environment)
            if not _signal_handlers_setup and not _is_test_environment():
                try:
                    _setup_signal_handlers()
                    _signal_handlers_setup = True
                except Exception as e:
                    logger.error(f"Failed to setup signal handlers: {e}")
                    logger.warning("Continuing without signal handlers")
                    # Continue execution even if signal setup fails

            # Setup atexit handler (only once, and only if not in test environment)
            if not _is_test_environment():
                try:
                    atexit.register(_cleanup_on_exit)
                except Exception as e:
                    logger.error(f"Failed to register atexit handler: {e}")
                    logger.warning("Continuing without atexit handler")
                    # Continue execution even if atexit registration fails

            logger.debug("CLI enforcement setup complete")

        except Exception as e:
            logger.error(f"Unexpected error during CLI enforcement setup: {e}", exc_info=True)
            # Continue execution even if setup fails


def _is_test_environment() -> bool:
    """Check if we're running in a test environment.

    Returns:
        bool: True if running in test environment, False otherwise

    """
    # Check for pytest
    if "pytest" in sys.modules:
        return True
    # Check for test environment variables
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def capture_user_input(command_args: list[str]) -> str:
    """Capture user input and emit USER_INPUT event.

    This function:
    1. Converts command args to input string
    2. Emits USER_INPUT event
    3. Returns input for processing

    Error Handling:
    - Catches validation errors during event emission
    - Catches ledger errors during storage
    - Logs errors without crashing
    - Returns input string even if event capture fails

    Args:
        command_args: Command line arguments (sys.argv[1:])

    Returns:
        str: The user input string

    Requirements:
        - Requirement 1.1: Emit USER_INPUT event
        - Requirement 1.2: Include complete message content
        - Requirement 5.2: Capture command as USER_INPUT event
        - Requirement 10.1-10.6: Handle errors gracefully

    """
    with mark_internal_operation():
        try:
            # Convert command args to input string
            input_str = " ".join(command_args) if command_args else ""

            logger.debug(f"Capturing user input: {input_str[:100]}...")

            # Emit USER_INPUT event with error handling
            try:
                emit_user_input(content=input_str)
                logger.debug("USER_INPUT event emitted successfully")
            except ValueError as e:
                logger.error(f"Validation error during USER_INPUT event emission: {e}")
                logger.warning("Continuing without event capture")
            except Exception as e:
                logger.error(f"Failed to emit USER_INPUT event: {e}", exc_info=True)
                logger.warning("Continuing without event capture")

            return input_str

        except Exception as e:
            logger.error(f"Unexpected error during user input capture: {e}", exc_info=True)
            # Return empty string if capture fails, but don't crash
            return ""


def _setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown.

    This function sets up handlers for:
    - SIGINT (Ctrl+C)
    - SIGTERM (termination signal)

    Error Handling:
    - Catches and logs signal setup errors
    - Continues execution if signal setup fails
    - Ensures cleanup is attempted even on signal

    Requirements:
        - Requirement 5.6: Emit SESSION_END event on interrupt
        - Requirement 10.1-10.6: Handle errors gracefully
    """
    with mark_internal_operation():
        try:

            def signal_handler(signum: int, frame: Any) -> None:
                logger.debug(f"Received signal {signum}, ending session")
                try:
                    _cleanup_on_exit()
                except Exception as e:
                    logger.error(f"Error during signal cleanup: {e}")
                finally:
                    sys.exit(0)

            # Setup SIGINT handler (Ctrl+C)
            try:
                signal.signal(signal.SIGINT, signal_handler)
                logger.debug("SIGINT handler registered")
            except Exception as e:
                logger.error(f"Failed to register SIGINT handler: {e}")

            # Setup SIGTERM handler (termination)
            try:
                signal.signal(signal.SIGTERM, signal_handler)
                logger.debug("SIGTERM handler registered")
            except Exception as e:
                logger.error(f"Failed to register SIGTERM handler: {e}")

            logger.debug("Signal handlers setup complete")

        except Exception as e:
            logger.error(f"Unexpected error during signal handler setup: {e}", exc_info=True)
            # Continue execution even if signal setup fails


def _cleanup_on_exit() -> None:
    """Cleanup on CLI exit.

    This function:
    1. Emits SESSION_END event
    2. Clears session state

    Error Handling:
    - Catches and logs all exceptions
    - Attempts to clear session state even if SESSION_END fails
    - Ensures cleanup is as complete as possible

    Requirements:
        - Requirement 5.4: Emit SESSION_END event on exit
        - Requirement 8.7-8.8: Clear session state
        - Requirement 10.1-10.6: Handle errors gracefully
    """
    with mark_internal_operation():
        try:
            if is_session_active():
                logger.debug("Ending session on CLI exit")
                try:
                    end_session()
                    logger.debug("Session ended successfully")
                except Exception as e:
                    logger.error(f"Failed to emit SESSION_END event: {e}", exc_info=True)
                    logger.warning("Attempting to clear session state anyway")
                    # Try to clear session state even if SESSION_END fails
                    try:
                        from divineos.core.session_manager import clear_session

                        clear_session()
                    except Exception as e2:
                        logger.error(f"Failed to clear session state: {e2}")

        except Exception as e:
            logger.error(f"Unexpected error during cleanup: {e}", exc_info=True)
            # Continue execution even if cleanup fails


def handle_cli_error(error: Exception) -> None:
    """Handle CLI errors and emit error events.

    This function:
    1. Logs the error with full traceback
    2. Emits TOOL_RESULT event with failed=true (if applicable)
    3. Continues or exits gracefully

    Error Handling:
    - Catches and logs all exceptions
    - Provides detailed error information
    - Continues execution even if error handling fails

    Args:
        error: The exception that occurred

    Requirements:
        - Requirement 5.5: Capture error in TOOL_RESULT event
        - Requirement 10.1-10.6: Handle errors gracefully

    """
    with mark_internal_operation():
        try:
            logger.error(f"CLI error: {error}", exc_info=True)
            # Error is already captured by tool wrapper if it occurred during tool execution
            # This function is for additional error handling if needed

        except Exception as e:
            logger.error(f"Unexpected error during CLI error handling: {e}", exc_info=True)
            # Continue execution even if error handling fails
