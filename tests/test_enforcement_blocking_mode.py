"""Unit tests for ClarityEnforcer BLOCKING mode.

Tests validate:
- BLOCKING mode prevents execution by raising ClarityViolationException
- Violations are logged and events are emitted
- ClarityViolationException includes violation details
- Error message is clear and actionable
"""

from unittest.mock import patch

import pytest

from divineos.clarity_enforcement.config import (
    ClarityConfig,
    ClarityEnforcementMode,
)
from divineos.clarity_enforcement.enforcer import (
    ClarityEnforcer,
    ClarityViolationException,
    enforce_clarity,
)
from divineos.clarity_enforcement.violation_detector import (
    ClarityViolation,
    ViolationSeverity,
)


class TestBlockingModeBasics:
    """Test basic BLOCKING mode functionality."""

    def test_enforcer_initialized_with_blocking_mode(self):
        """Test that enforcer can be initialized with BLOCKING mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        assert enforcer.config.enforcement_mode == ClarityEnforcementMode.BLOCKING

    def test_blocking_mode_raises_exception_for_unexplained_calls(self):
        """Test that BLOCKING mode raises ClarityViolationException for unexplained calls."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        # Create a violation (unexplained tool call)
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "important_file.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        # Mock the violation detector to return a violation
        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation"):
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    with pytest.raises(ClarityViolationException):
                        enforcer.enforce(
                            tool_name="deleteFile",
                            tool_input={"path": "important_file.txt"},
                            context=[],
                            session_id="test-session-123",
                        )

    def test_blocking_mode_allows_explained_calls(self):
        """Test that BLOCKING mode allows explained tool calls."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        # Mock the violation detector to return None (no violation)
        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=None,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    result = enforcer.enforce(
                        tool_name="readFile",
                        tool_input={"path": "file.txt"},
                        context=["I need to read the file"],
                        session_id="test-session-123",
                    )
                    assert result is None
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()


class TestClarityViolationException:
    """Test ClarityViolationException details and message."""

    def test_exception_includes_violation_details(self):
        """Test that exception includes violation details."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "important_file.txt"},
            severity=ViolationSeverity.HIGH,
            context=["some context"],
            session_id="test-session-123",
        )

        exception = ClarityViolationException(violation)

        assert exception.violation == violation
        assert exception.violation.tool_name == "deleteFile"
        assert exception.violation.severity == ViolationSeverity.HIGH

    def test_exception_message_is_clear_and_actionable(self):
        """Test that exception message is clear and actionable."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "important_file.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        exception = ClarityViolationException(
            violation,
            "BLOCKING mode: Tool call deleteFile lacks explanation. "
            "Please provide a clear explanation of why this tool is being called.",
        )

        assert "BLOCKING mode" in str(exception)
        assert "deleteFile" in str(exception)
        assert "explanation" in str(exception).lower()

    def test_exception_message_default_format(self):
        """Test that exception has default message format."""
        violation = ClarityViolation(
            tool_name="fsWrite",
            tool_input={"path": "config.json"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        exception = ClarityViolationException(violation)

        assert "fsWrite" in str(exception)
        assert "unexplained" in str(exception).lower()

    def test_exception_custom_message(self):
        """Test that exception accepts custom message."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        custom_message = "Custom error message for testing"
        exception = ClarityViolationException(violation, custom_message)

        assert exception.message == custom_message
        assert str(exception) == custom_message


class TestBlockingModeViolationLogging:
    """Test that violations are logged in BLOCKING mode."""

    def test_violation_is_logged_in_blocking_mode(self):
        """Test that violations are logged when detected in BLOCKING mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    with pytest.raises(ClarityViolationException):
                        enforcer.enforce(
                            tool_name="deleteFile",
                            tool_input={"path": "file.txt"},
                            context=[],
                            session_id="test-session-123",
                        )

                    # Verify logging was called
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args
                    assert call_args[0][0] == violation
                    assert call_args[0][1] == ClarityEnforcementMode.BLOCKING
                    assert call_args[0][2] == "blocked"

    def test_violation_logging_includes_enforcement_mode(self):
        """Test that violation logging includes enforcement mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="fsWrite",
            tool_input={"path": "config.json", "text": "data"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    with pytest.raises(ClarityViolationException):
                        enforcer.enforce(
                            tool_name="fsWrite",
                            tool_input={"path": "config.json", "text": "data"},
                            context=[],
                            session_id="test-session-123",
                        )

                    # Verify enforcement mode is passed to logging
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args
                    assert call_args[0][1] == ClarityEnforcementMode.BLOCKING


class TestBlockingModeEventEmission:
    """Test that CLARITY_VIOLATION events are emitted in BLOCKING mode."""

    def test_clarity_violation_event_is_emitted(self):
        """Test that CLARITY_VIOLATION event is emitted in BLOCKING mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation"):
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    with pytest.raises(ClarityViolationException):
                        enforcer.enforce(
                            tool_name="deleteFile",
                            tool_input={"path": "file.txt"},
                            context=[],
                            session_id="test-session-123",
                        )

                    # Verify event emission was called
                    mock_emit.assert_called_once()
                    call_args = mock_emit.call_args
                    assert call_args[0][0] == violation
                    assert call_args[0][1] == ClarityEnforcementMode.BLOCKING
                    assert call_args[0][2] == "blocked"

    def test_event_emission_disabled_when_config_disabled(self):
        """Test that event emission respects config setting."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=False,  # Disabled
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation"):
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    with pytest.raises(ClarityViolationException):
                        enforcer.enforce(
                            tool_name="deleteFile",
                            tool_input={"path": "file.txt"},
                            context=[],
                            session_id="test-session-123",
                        )

                    # Verify event emission was NOT called
                    mock_emit.assert_not_called()


class TestBlockingModeDifferentToolTypes:
    """Test BLOCKING mode with different tool types and severities."""

    def test_blocking_mode_high_severity_tool(self):
        """Test BLOCKING mode with HIGH severity tool (deleteFile)."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "important.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation"):
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    with pytest.raises(ClarityViolationException) as exc_info:
                        enforcer.enforce(
                            tool_name="deleteFile",
                            tool_input={"path": "important.txt"},
                            context=[],
                            session_id="test-session-123",
                        )

                    assert exc_info.value.violation.severity == ViolationSeverity.HIGH

    def test_blocking_mode_medium_severity_tool(self):
        """Test BLOCKING mode with MEDIUM severity tool (executePwsh)."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="executePwsh",
            tool_input={"command": "npm test"},
            severity=ViolationSeverity.MEDIUM,
            context=[],
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation"):
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    with pytest.raises(ClarityViolationException) as exc_info:
                        enforcer.enforce(
                            tool_name="executePwsh",
                            tool_input={"command": "npm test"},
                            context=[],
                            session_id="test-session-123",
                        )

                    assert exc_info.value.violation.severity == ViolationSeverity.MEDIUM

    def test_blocking_mode_low_severity_tool(self):
        """Test BLOCKING mode with LOW severity tool (readFile)."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="readFile",
            tool_input={"path": "config.json"},
            severity=ViolationSeverity.LOW,
            context=[],
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation"):
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    with pytest.raises(ClarityViolationException) as exc_info:
                        enforcer.enforce(
                            tool_name="readFile",
                            tool_input={"path": "config.json"},
                            context=[],
                            session_id="test-session-123",
                        )

                    assert exc_info.value.violation.severity == ViolationSeverity.LOW


class TestBlockingModeContextCapture:
    """Test that context is properly captured in violations."""

    def test_context_captured_in_violation(self):
        """Test that context is captured in violation."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        context = [
            "User: I need to delete a file",
            "Assistant: I can help with that",
        ]

        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.HIGH,
            context=context,
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    with pytest.raises(ClarityViolationException):
                        enforcer.enforce(
                            tool_name="deleteFile",
                            tool_input={"path": "file.txt"},
                            context=context,
                            session_id="test-session-123",
                        )

                    # Verify context is in the violation
                    call_args = mock_log.call_args
                    logged_violation = call_args[0][0]
                    assert logged_violation.context == context

    def test_session_id_included_in_violation(self):
        """Test that session_id is included in violation."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        session_id = "test-session-abc-123"
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id=session_id,
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    with pytest.raises(ClarityViolationException):
                        enforcer.enforce(
                            tool_name="deleteFile",
                            tool_input={"path": "file.txt"},
                            context=[],
                            session_id=session_id,
                        )

                    # Verify session_id is in the violation
                    call_args = mock_log.call_args
                    logged_violation = call_args[0][0]
                    assert logged_violation.session_id == session_id


class TestBlockingModeEnforceFunction:
    """Test the module-level enforce_clarity function."""

    def test_enforce_clarity_function_with_blocking_mode(self):
        """Test enforce_clarity function with BLOCKING mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )

        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation"):
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    with pytest.raises(ClarityViolationException):
                        enforce_clarity(
                            tool_name="deleteFile",
                            tool_input={"path": "file.txt"},
                            context=[],
                            session_id="test-session-123",
                            config=config,
                        )

    def test_enforce_clarity_function_loads_config_if_not_provided(self):
        """Test that enforce_clarity loads config if not provided."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        with patch("divineos.clarity_enforcement.enforcer.get_clarity_config") as mock_get_config:
            mock_config = ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.BLOCKING,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
            mock_get_config.return_value = mock_config

            with patch(
                "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
                return_value=violation,
            ):
                with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation"):
                    with patch(
                        "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                    ):
                        with pytest.raises(ClarityViolationException):
                            enforce_clarity(
                                tool_name="deleteFile",
                                tool_input={"path": "file.txt"},
                                context=[],
                                session_id="test-session-123",
                            )

                        # Verify config was loaded
                        mock_get_config.assert_called_once()


class TestBlockingModeExceptionDetails:
    """Test detailed exception information."""

    def test_exception_contains_tool_name(self):
        """Test that exception message contains tool name."""
        violation = ClarityViolation(
            tool_name="semanticRename",
            tool_input={"oldName": "foo", "newName": "bar"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        exception = ClarityViolationException(
            violation,
            "BLOCKING mode: Tool call semanticRename lacks explanation. "
            "Please provide a clear explanation of why this tool is being called.",
        )

        assert "semanticRename" in str(exception)

    def test_exception_contains_tool_input_in_violation(self):
        """Test that exception violation contains tool input."""
        tool_input = {"path": "important_file.txt", "mode": "delete"}
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input=tool_input,
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        exception = ClarityViolationException(violation)

        assert exception.violation.tool_input == tool_input

    def test_exception_contains_severity_in_violation(self):
        """Test that exception violation contains severity."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        exception = ClarityViolationException(violation)

        assert exception.violation.severity == ViolationSeverity.HIGH

    def test_exception_is_subclass_of_exception(self):
        """Test that ClarityViolationException is a proper Exception."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        exception = ClarityViolationException(violation)

        assert isinstance(exception, Exception)


class TestBlockingModeMultipleViolations:
    """Test BLOCKING mode with multiple violations."""

    def test_first_violation_raises_exception(self):
        """Test that first violation raises exception."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file1.txt"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation"):
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    with pytest.raises(ClarityViolationException):
                        enforcer.enforce(
                            tool_name="deleteFile",
                            tool_input={"path": "file1.txt"},
                            context=[],
                            session_id="test-session-123",
                        )

    def test_second_violation_also_raises_exception(self):
        """Test that second violation also raises exception."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.BLOCKING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="fsWrite",
            tool_input={"path": "file2.txt", "text": "data"},
            severity=ViolationSeverity.HIGH,
            context=[],
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation"):
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    with pytest.raises(ClarityViolationException):
                        enforcer.enforce(
                            tool_name="fsWrite",
                            tool_input={"path": "file2.txt", "text": "data"},
                            context=[],
                            session_id="test-session-123",
                        )
