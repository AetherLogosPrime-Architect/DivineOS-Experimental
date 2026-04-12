"""Unit tests for ClarityEnforcer LOGGING mode.

Tests validate:
- LOGGING mode allows unexplained tool calls to execute
- Violations are logged and events are emitted
- No exception is raised
- Violations are queryable via logs
- Different tool types (HIGH, MEDIUM, LOW severity) are handled
- Context capture in logs
- session_id is included
- Explained calls don't log violations
- Enforcement mode is included in logs
"""

from unittest.mock import patch

from divineos.clarity_enforcement.config import (
    ClarityConfig,
    ClarityEnforcementMode,
)
from divineos.clarity_enforcement.enforcer import (
    ClarityEnforcer,
    enforce_clarity,
)
from divineos.clarity_enforcement.violation_detector import (
    ClarityViolation,
    ViolationSeverity,
)


class TestLoggingModeBasics:
    """Test basic LOGGING mode functionality."""

    def test_enforcer_initialized_with_logging_mode(self):
        """Test that enforcer can be initialized with LOGGING mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        assert enforcer.config.enforcement_mode == ClarityEnforcementMode.LOGGING

    def test_logging_mode_allows_unexplained_calls(self):
        """Test that LOGGING mode allows unexplained tool calls to execute."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    # Should NOT raise exception
                    result = enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "important_file.txt"},
                        context=[],
                        session_id="test-session-123",
                    )
                    # Logging mode should still log and emit, just not raise
                    assert mock_log.called or mock_emit.called or result is None

    def test_logging_mode_allows_explained_calls(self):
        """Test that LOGGING mode allows explained tool calls."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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

    def test_logging_mode_does_not_raise_exception(self):
        """Test that LOGGING mode does not raise exception for violations."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    result = enforcer.enforce(
                        tool_name="fsWrite",
                        tool_input={"path": "config.json", "text": "data"},
                        context=[],
                        session_id="test-session-123",
                    )
                    assert result is None
                    mock_log.assert_called_once()
                    mock_emit.assert_called_once()


class TestLoggingModeViolationLogging:
    """Test that violations are logged in LOGGING mode."""

    def test_violation_is_logged_in_logging_mode(self):
        """Test that violations are logged when detected in LOGGING mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
                    assert call_args[0][1] == ClarityEnforcementMode.LOGGING
                    assert call_args[0][2] == "logged"

    def test_violation_logging_includes_enforcement_mode(self):
        """Test that violation logging includes enforcement mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
                    enforcer.enforce(
                        tool_name="fsWrite",
                        tool_input={"path": "config.json", "text": "data"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify enforcement mode is passed to logging
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args
                    assert call_args[0][1] == ClarityEnforcementMode.LOGGING

    def test_no_violation_not_logged(self):
        """Test that explained calls are not logged as violations."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=None,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    enforcer.enforce(
                        tool_name="readFile",
                        tool_input={"path": "file.txt"},
                        context=["I need to read the file"],
                        session_id="test-session-123",
                    )

                    # Verify logging was NOT called
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()


class TestLoggingModeEventEmission:
    """Test that CLARITY_VIOLATION events are emitted in LOGGING mode."""

    def test_clarity_violation_event_is_emitted(self):
        """Test that CLARITY_VIOLATION event is emitted in LOGGING mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
                    assert call_args[0][1] == ClarityEnforcementMode.LOGGING
                    assert call_args[0][2] == "logged"

    def test_event_emission_disabled_when_config_disabled(self):
        """Test that event emission respects config setting."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify event emission was NOT called
                    mock_emit.assert_not_called()

    def test_event_includes_violation_details(self):
        """Test that emitted event includes violation details."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="fsWrite",
            tool_input={"path": "config.json", "text": "data"},
            severity=ViolationSeverity.HIGH,
            context=["some context"],
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
                    enforcer.enforce(
                        tool_name="fsWrite",
                        tool_input={"path": "config.json", "text": "data"},
                        context=["some context"],
                        session_id="test-session-123",
                    )

                    # Verify violation details are passed to event emission
                    mock_emit.assert_called_once()
                    call_args = mock_emit.call_args
                    emitted_violation = call_args[0][0]
                    assert emitted_violation.tool_name == "fsWrite"
                    assert emitted_violation.severity == ViolationSeverity.HIGH


class TestLoggingModeDifferentToolTypes:
    """Test LOGGING mode with different tool types and severities."""

    def test_logging_mode_high_severity_tool(self):
        """Test LOGGING mode with HIGH severity tool (deleteFile)."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    # Should not raise exception
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "important.txt"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify logging was called with HIGH severity
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args
                    assert call_args[0][0].severity == ViolationSeverity.HIGH

    def test_logging_mode_medium_severity_tool(self):
        """Test LOGGING mode with MEDIUM severity tool (executePwsh)."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    # Should not raise exception
                    enforcer.enforce(
                        tool_name="executePwsh",
                        tool_input={"command": "npm test"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify logging was called with MEDIUM severity
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args
                    assert call_args[0][0].severity == ViolationSeverity.MEDIUM

    def test_logging_mode_low_severity_tool(self):
        """Test LOGGING mode with LOW severity tool (readFile)."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    # Should not raise exception
                    enforcer.enforce(
                        tool_name="readFile",
                        tool_input={"path": "config.json"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify logging was called with LOW severity
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args
                    assert call_args[0][0].severity == ViolationSeverity.LOW

    def test_logging_mode_multiple_high_severity_tools(self):
        """Test LOGGING mode with multiple HIGH severity tools."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        high_severity_tools = ["deleteFile", "fsWrite", "fsAppend", "semanticRename"]

        for tool_name in high_severity_tools:
            violation = ClarityViolation(
                tool_name=tool_name,
                tool_input={"path": "file.txt"},
                severity=ViolationSeverity.HIGH,
                context=[],
                session_id="test-session-123",
            )

            with patch(
                "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
                return_value=violation,
            ):
                with patch(
                    "divineos.clarity_enforcement.enforcer.log_clarity_violation"
                ) as mock_log:
                    with patch(
                        "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                    ):
                        # Should not raise exception
                        enforcer.enforce(
                            tool_name=tool_name,
                            tool_input={"path": "file.txt"},
                            context=[],
                            session_id="test-session-123",
                        )

                        # Verify logging was called
                        mock_log.assert_called_once()


class TestLoggingModeContextCapture:
    """Test that context is properly captured in violations."""

    def test_context_captured_in_violation(self):
        """Test that context is captured in violation."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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

    def test_context_and_session_id_in_event(self):
        """Test that context and session_id are included in emitted event."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        context = ["User: I need to read a file", "Assistant: I'll help"]
        session_id = "session-xyz-789"

        violation = ClarityViolation(
            tool_name="readFile",
            tool_input={"path": "data.json"},
            severity=ViolationSeverity.LOW,
            context=context,
            session_id=session_id,
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation"):
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    enforcer.enforce(
                        tool_name="readFile",
                        tool_input={"path": "data.json"},
                        context=context,
                        session_id=session_id,
                    )

                    # Verify context and session_id are in the event
                    call_args = mock_emit.call_args
                    emitted_violation = call_args[0][0]
                    assert emitted_violation.context == context
                    assert emitted_violation.session_id == session_id


class TestLoggingModeEnforceFunction:
    """Test the module-level enforce_clarity function."""

    def test_enforce_clarity_function_with_logging_mode(self):
        """Test enforce_clarity function with LOGGING mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    # Should not raise exception
                    enforce_clarity(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id="test-session-123",
                        config=config,
                    )

                    # Verify logging was called
                    mock_log.assert_called_once()

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
                enforcement_mode=ClarityEnforcementMode.LOGGING,
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
                        # Should not raise exception
                        enforce_clarity(
                            tool_name="deleteFile",
                            tool_input={"path": "file.txt"},
                            context=[],
                            session_id="test-session-123",
                        )

                        # Verify config was loaded
                        mock_get_config.assert_called_once()


class TestLoggingModeViolationQueryability:
    """Test that violations are queryable via logs."""

    def test_violation_logged_with_tool_name(self):
        """Test that violation is logged with tool name for queryability."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify tool name is in logged violation
                    call_args = mock_log.call_args
                    logged_violation = call_args[0][0]
                    assert logged_violation.tool_name == "deleteFile"

    def test_violation_logged_with_severity(self):
        """Test that violation is logged with severity for queryability."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="fsWrite",
            tool_input={"path": "config.json"},
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
                    enforcer.enforce(
                        tool_name="fsWrite",
                        tool_input={"path": "config.json"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify severity is in logged violation
                    call_args = mock_log.call_args
                    logged_violation = call_args[0][0]
                    assert logged_violation.severity == ViolationSeverity.HIGH

    def test_violation_logged_with_timestamp(self):
        """Test that violation is logged with timestamp for queryability."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="readFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.LOW,
            context=[],
            session_id="test-session-123",
        )

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=violation,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch("divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"):
                    enforcer.enforce(
                        tool_name="readFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify timestamp is in logged violation
                    call_args = mock_log.call_args
                    logged_violation = call_args[0][0]
                    assert logged_violation.timestamp is not None
                    assert len(logged_violation.timestamp) > 0

    def test_violation_to_dict_for_queryability(self):
        """Test that violation can be converted to dict for queryability."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "file.txt"},
            severity=ViolationSeverity.HIGH,
            context=["context1", "context2"],
            session_id="test-session-123",
        )

        violation_dict = violation.to_dict()

        assert violation_dict["tool_name"] == "deleteFile"
        assert violation_dict["severity"] == "HIGH"
        assert violation_dict["session_id"] == "test-session-123"
        assert violation_dict["context"] == ["context1", "context2"]
        assert "timestamp" in violation_dict


class TestLoggingModeExplainedCalls:
    """Test that explained calls don't log violations."""

    def test_explained_call_no_violation_logged(self):
        """Test that explained calls don't result in violation logging."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=None,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    enforcer.enforce(
                        tool_name="readFile",
                        tool_input={"path": "file.txt"},
                        context=["I need to read the file to understand the structure"],
                        session_id="test-session-123",
                    )

                    # Verify logging was NOT called
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()

    def test_multiple_explained_calls_no_violations(self):
        """Test that multiple explained calls don't log violations."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        explained_calls = [
            ("readFile", {"path": "file1.txt"}),
            ("readFile", {"path": "file2.txt"}),
            ("listDirectory", {"path": "."}),
        ]

        for tool_name, tool_input in explained_calls:
            with patch(
                "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
                return_value=None,
            ):
                with patch(
                    "divineos.clarity_enforcement.enforcer.log_clarity_violation"
                ) as mock_log:
                    with patch(
                        "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                    ) as mock_emit:
                        enforcer.enforce(
                            tool_name=tool_name,
                            tool_input=tool_input,
                            context=["I need to check the files"],
                            session_id="test-session-123",
                        )

                        # Verify logging was NOT called
                        mock_log.assert_not_called()
                        mock_emit.assert_not_called()

    def test_explained_call_with_detailed_context(self):
        """Test that explained calls with detailed context don't log violations."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        detailed_context = [
            "User: I need to analyze the configuration",
            "Assistant: I'll help you analyze the configuration",
            "User: Please read the config file",
            "Assistant: I'll read the config file to understand the settings",
        ]

        with patch(
            "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
            return_value=None,
        ):
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    enforcer.enforce(
                        tool_name="readFile",
                        tool_input={"path": "config.json"},
                        context=detailed_context,
                        session_id="test-session-123",
                    )

                    # Verify logging was NOT called
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()


class TestLoggingModeEnforcementModeInLogs:
    """Test that enforcement mode is included in logs."""

    def test_enforcement_mode_passed_to_logging(self):
        """Test that LOGGING enforcement mode is passed to logging function."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify enforcement mode is passed
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args
                    enforcement_mode = call_args[0][1]
                    assert enforcement_mode == ClarityEnforcementMode.LOGGING

    def test_action_taken_is_logged(self):
        """Test that action taken is logged as 'logged'."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="fsWrite",
            tool_input={"path": "config.json"},
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
                    enforcer.enforce(
                        tool_name="fsWrite",
                        tool_input={"path": "config.json"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify action taken is "logged"
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args
                    action_taken = call_args[0][2]
                    assert action_taken == "logged"

    def test_enforcement_mode_in_event_emission(self):
        """Test that enforcement mode is included in event emission."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
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
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify enforcement mode is passed to event emission
                    mock_emit.assert_called_once()
                    call_args = mock_emit.call_args
                    enforcement_mode = call_args[0][1]
                    assert enforcement_mode == ClarityEnforcementMode.LOGGING

    def test_action_taken_in_event_emission(self):
        """Test that action taken is included in event emission."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.LOGGING,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        violation = ClarityViolation(
            tool_name="fsWrite",
            tool_input={"path": "config.json"},
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
                    enforcer.enforce(
                        tool_name="fsWrite",
                        tool_input={"path": "config.json"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify action taken is "logged" in event emission
                    mock_emit.assert_called_once()
                    call_args = mock_emit.call_args
                    action_taken = call_args[0][2]
                    assert action_taken == "logged"
