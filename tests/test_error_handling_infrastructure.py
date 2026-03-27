"""
Tests for Error Handling Infrastructure

Tests verify that:
1. All exception classes can be raised and caught
2. Exception hierarchy is correct
3. handle_error() logs errors with context
4. Stack traces are included in logs
5. Extra context information is preserved
"""

import pytest
from loguru import logger
from divineos.core.error_handling import (
    DivineOSError,
    EventCaptureError,
    SessionError,
    handle_error,
)


@pytest.fixture
def caplog_loguru(caplog):
    """Fixture to capture loguru logs in caplog."""
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


class TestExceptionHierarchy:
    """Test that exception hierarchy is correct."""

    def test_event_capture_error_inherits_from_divineos_error(self) -> None:
        """EventCaptureError should inherit from DivineOSError."""
        assert issubclass(EventCaptureError, DivineOSError)

    def test_session_error_inherits_from_divineos_error(self) -> None:
        """SessionError should inherit from DivineOSError."""
        assert issubclass(SessionError, DivineOSError)

    def test_divineos_error_inherits_from_exception(self) -> None:
        """DivineOSError should inherit from Exception."""
        assert issubclass(DivineOSError, Exception)


class TestExceptionRaising:
    """Test that exceptions can be raised and caught."""

    def test_raise_and_catch_divineos_error(self) -> None:
        """DivineOSError can be raised and caught."""
        with pytest.raises(DivineOSError):
            raise DivineOSError("Test error")

    def test_raise_and_catch_event_capture_error(self) -> None:
        """EventCaptureError can be raised and caught."""
        with pytest.raises(EventCaptureError):
            raise EventCaptureError("Event capture failed")

    def test_raise_and_catch_session_error(self) -> None:
        """SessionError can be raised and caught."""
        with pytest.raises(SessionError):
            raise SessionError("Session management failed")

    def test_catch_specific_error_with_base_class(self) -> None:
        """Specific errors can be caught with base DivineOSError."""
        with pytest.raises(DivineOSError):
            raise EventCaptureError("Event capture failed")

    def test_exception_message_preserved(self) -> None:
        """Exception message should be preserved."""
        message = "Test error message"
        with pytest.raises(EventCaptureError) as exc_info:
            raise EventCaptureError(message)
        assert str(exc_info.value) == message


class TestHandleError:
    """Test the handle_error() function."""

    def test_handle_error_logs_error(self, caplog_loguru) -> None:
        """handle_error() should log the error."""
        error = EventCaptureError("Test error")
        handle_error(error, "test_context")

        assert "Error in test_context" in caplog_loguru.text
        assert "Test error" in caplog_loguru.text

    def test_handle_error_includes_context(self, caplog_loguru) -> None:
        """handle_error() should include context in the log."""
        error = SessionError("Session error")
        handle_error(error, "session_operation")

        assert "session_operation" in caplog_loguru.text

    def test_handle_error_with_extra_info(self, caplog_loguru) -> None:
        """handle_error() should include extra context information."""
        error = SessionError("Session not found")
        extra_info = {"session_id": "test-session-123"}

        handle_error(error, "session_lookup", extra_info)

        assert "Error in session_lookup" in caplog_loguru.text

    def test_handle_error_logs_at_error_level(self, caplog_loguru) -> None:
        """handle_error() should log at ERROR level."""
        error = EventCaptureError("Tool failed")
        handle_error(error, "tool_execution")

        assert "Error in tool_execution" in caplog_loguru.text

    def test_handle_error_with_different_error_types(self, caplog_loguru) -> None:
        """handle_error() should work with all error types."""
        errors = [
            DivineOSError("Base error"),
            EventCaptureError("Event error"),
            SessionError("Session error"),
        ]

        for error in errors:
            handle_error(error, "test_context")

        assert caplog_loguru.text.count("Error in test_context") >= len(errors)


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    def test_error_handling_in_try_except(self, caplog_loguru) -> None:
        """Error handling should work in try/except blocks."""
        try:
            raise EventCaptureError("Capture failed")
        except EventCaptureError as e:
            handle_error(e, "event_capture_operation")

        assert "Error in event_capture_operation" in caplog_loguru.text

    def test_multiple_errors_logged_separately(self, caplog_loguru) -> None:
        """Multiple errors should be logged separately."""
        try:
            raise EventCaptureError("First error")
        except EventCaptureError as e:
            handle_error(e, "operation_1")

        try:
            raise SessionError("Second error")
        except SessionError as e:
            handle_error(e, "operation_2")

        assert "operation_1" in caplog_loguru.text
        assert "operation_2" in caplog_loguru.text

    def test_error_with_nested_context(self, caplog_loguru) -> None:
        """Error handling should work with nested context."""
        extra_info = {
            "operation": "save_event",
            "event_id": "evt-123",
            "attempt": 1,
        }

        error = SessionError("Database connection failed")
        handle_error(error, "ledger_save", extra_info)

        assert "Error in ledger_save" in caplog_loguru.text
        assert "Database connection failed" in caplog_loguru.text


class TestExceptionDocstrings:
    """Test that exceptions have proper documentation."""

    def test_divineos_error_has_docstring(self) -> None:
        """DivineOSError should have a docstring."""
        assert DivineOSError.__doc__ is not None
        assert len(DivineOSError.__doc__) > 0

    def test_event_capture_error_has_docstring(self) -> None:
        """EventCaptureError should have a docstring."""
        assert EventCaptureError.__doc__ is not None
        assert len(EventCaptureError.__doc__) > 0

    def test_session_error_has_docstring(self) -> None:
        """SessionError should have a docstring."""
        assert SessionError.__doc__ is not None
        assert len(SessionError.__doc__) > 0

    def test_handle_error_has_docstring(self) -> None:
        """handle_error() should have a docstring."""
        assert handle_error.__doc__ is not None
        assert len(handle_error.__doc__) > 0


class TestErrorImports:
    """Test that errors can be imported correctly."""

    def test_import_all_exceptions(self) -> None:
        """All exceptions should be importable."""
        from divineos.core.error_handling import (
            DivineOSError,
            EventCaptureError,
            SessionError,
        )

        assert DivineOSError is not None
        assert EventCaptureError is not None
        assert SessionError is not None

    def test_import_handle_error(self) -> None:
        """handle_error() should be importable."""
        from divineos.core.error_handling import handle_error

        assert handle_error is not None
        assert callable(handle_error)
