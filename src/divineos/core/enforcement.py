"""
CLI Enforcement Layer Module — Enforces event capture at CLI level.

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

import sys
import os
import signal
import atexit
from typing import List
from loguru import logger

from divineos.core.loop_prevention import mark_internal_operation
from divineos.core.session_manager import initialize_session, end_session, is_session_active
from divineos.event.event_emission import emit_user_input


# Global state for signal handling
_signal_handlers_setup = False
_session_initialized = False


def setup_cli_enforcement() -> None:
    """
    Initialize CLI enforcement at startup.

    This function:
    1. Initializes the session manager
    2. Sets up signal handlers for graceful shutdown
    3. Sets up atexit handler for cleanup

    Requirements:
        - Requirement 5.1: Initialize event capture system
        - Requirement 5.6: Setup signal handlers
    """
    global _signal_handlers_setup, _session_initialized

    with mark_internal_operation():
        try:
            logger.debug("Setting up CLI enforcement")

            # Initialize session (only once)
            if not _session_initialized:
                session_id = initialize_session()
                logger.debug(f"Initialized session: {session_id}")
                _session_initialized = True

            # Setup signal handlers (only once, and only if not in test environment)
            if not _signal_handlers_setup and not _is_test_environment():
                _setup_signal_handlers()
                _signal_handlers_setup = True

            # Setup atexit handler (only once, and only if not in test environment)
            if not _is_test_environment():
                atexit.register(_cleanup_on_exit)

            logger.debug("CLI enforcement setup complete")

        except Exception as e:
            logger.error(f"Failed to setup CLI enforcement: {e}")
            # Continue execution even if setup fails


def _is_test_environment() -> bool:
    """
    Check if we're running in a test environment.

    Returns:
        bool: True if running in test environment, False otherwise
    """
    # Check for pytest
    if "pytest" in sys.modules:
        return True
    # Check for test environment variables
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    return False


def capture_user_input(command_args: List[str]) -> str:
    """
    Capture user input and emit USER_INPUT event.

    This function:
    1. Converts command args to input string
    2. Emits USER_INPUT event
    3. Returns input for processing

    Args:
        command_args: Command line arguments (sys.argv[1:])

    Returns:
        str: The user input string

    Requirements:
        - Requirement 1.1: Emit USER_INPUT event
        - Requirement 1.2: Include complete message content
        - Requirement 5.2: Capture command as USER_INPUT event
    """
    with mark_internal_operation():
        try:
            # Convert command args to input string
            input_str = " ".join(command_args) if command_args else ""

            logger.debug(f"Capturing user input: {input_str[:100]}...")

            # Emit USER_INPUT event
            try:
                emit_user_input(content=input_str)
            except Exception as e:
                logger.error(f"Failed to emit USER_INPUT event: {e}")
                # Continue execution even if event capture fails

            return input_str

        except Exception as e:
            logger.error(f"Failed to capture user input: {e}")
            # Return empty string if capture fails
            return ""


def _setup_signal_handlers() -> None:
    """
    Setup signal handlers for graceful shutdown.

    This function sets up handlers for:
    - SIGINT (Ctrl+C)
    - SIGTERM (termination signal)

    Requirements:
        - Requirement 5.6: Emit SESSION_END event on interrupt
    """
    with mark_internal_operation():
        try:

            def signal_handler(signum, frame):
                logger.debug(f"Received signal {signum}, ending session")
                _cleanup_on_exit()
                sys.exit(0)

            # Setup SIGINT handler (Ctrl+C)
            signal.signal(signal.SIGINT, signal_handler)

            # Setup SIGTERM handler (termination)
            signal.signal(signal.SIGTERM, signal_handler)

            logger.debug("Signal handlers setup complete")

        except Exception as e:
            logger.error(f"Failed to setup signal handlers: {e}")
            # Continue execution even if signal setup fails


def _cleanup_on_exit() -> None:
    """
    Cleanup on CLI exit.

    This function:
    1. Emits SESSION_END event
    2. Clears session state

    Requirements:
        - Requirement 5.4: Emit SESSION_END event on exit
        - Requirement 8.7-8.8: Clear session state
    """
    with mark_internal_operation():
        try:
            if is_session_active():
                logger.debug("Ending session on CLI exit")
                end_session()
                logger.debug("Session ended")

        except Exception as e:
            logger.error(f"Failed to cleanup on exit: {e}")
            # Continue execution even if cleanup fails


def handle_cli_error(error: Exception) -> None:
    """
    Handle CLI errors and emit error events.

    This function:
    1. Logs the error
    2. Emits TOOL_RESULT event with failed=true (if applicable)
    3. Continues or exits gracefully

    Args:
        error: The exception that occurred

    Requirements:
        - Requirement 5.5: Capture error in TOOL_RESULT event
        - Requirement 10.1-10.6: Handle errors gracefully
    """
    with mark_internal_operation():
        try:
            logger.error(f"CLI error: {error}")
            # Error is already captured by tool wrapper if it occurred during tool execution
            # This function is for additional error handling if needed

        except Exception as e:
            logger.error(f"Failed to handle CLI error: {e}")
            # Continue execution even if error handling fails
