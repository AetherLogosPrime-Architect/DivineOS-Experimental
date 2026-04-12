"""Unit tests for ClarityEnforcer PERMISSIVE mode.

Tests validate:
- PERMISSIVE mode allows all tool calls without logging or blocking
- No violations are logged
- No events are emitted
- No exceptions are raised
- Backward compatibility is maintained
- Configuration defaults to PERMISSIVE
- Existing code continues to work
"""

from unittest.mock import Mock, patch

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


class TestPermissiveModeBasics:
    """Test basic PERMISSIVE mode functionality."""

    def test_enforcer_initialized_with_permissive_mode(self):
        """Test that enforcer can be initialized with PERMISSIVE mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        assert enforcer.config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE

    def test_permissive_mode_allows_unexplained_calls(self):
        """Test that PERMISSIVE mode allows unexplained tool calls to execute."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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
                    result = enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "important_file.txt"},
                        context=[],
                        session_id="test-session-123",
                    )
                    assert result is None
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()

    def test_permissive_mode_allows_explained_calls(self):
        """Test that PERMISSIVE mode allows explained tool calls."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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

    def test_permissive_mode_does_not_raise_exception(self):
        """Test that PERMISSIVE mode does not raise exception for violations."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()


class TestPermissiveModeNoViolationLogging:
    """Test that violations are NOT logged in PERMISSIVE mode."""

    def test_violation_not_logged_in_permissive_mode(self):
        """Test that violations are NOT logged when detected in PERMISSIVE mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify logging was NOT called
                    mock_log.assert_not_called()
                    # Verify event emission was NOT called
                    mock_emit.assert_not_called()

    def test_no_violation_not_logged_in_permissive_mode(self):
        """Test that explained calls are not logged as violations in PERMISSIVE mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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


class TestPermissiveModeNoEventEmission:
    """Test that CLARITY_VIOLATION events are NOT emitted in PERMISSIVE mode."""

    def test_clarity_violation_event_not_emitted_in_permissive_mode(self):
        """Test that CLARITY_VIOLATION event is NOT emitted in PERMISSIVE mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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

                    # Verify event emission was NOT called
                    mock_emit.assert_not_called()

    def test_event_emission_not_called_even_with_config_enabled(self):
        """Test that event emission is not called even when config has emit_events=True."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,  # Enabled, but should not be used in PERMISSIVE mode
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


class TestPermissiveModeDifferentToolTypes:
    """Test PERMISSIVE mode with different tool types and severities."""

    def test_permissive_mode_high_severity_tool(self):
        """Test PERMISSIVE mode with HIGH severity tool (deleteFile)."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    # Should not raise exception
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "important.txt"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify logging and event emission were NOT called
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()

    def test_permissive_mode_medium_severity_tool(self):
        """Test PERMISSIVE mode with MEDIUM severity tool (executePwsh)."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    # Should not raise exception
                    enforcer.enforce(
                        tool_name="executePwsh",
                        tool_input={"command": "npm test"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify logging and event emission were NOT called
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()

    def test_permissive_mode_low_severity_tool(self):
        """Test PERMISSIVE mode with LOW severity tool (readFile)."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    # Should not raise exception
                    enforcer.enforce(
                        tool_name="readFile",
                        tool_input={"path": "config.json"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify logging and event emission were NOT called
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()

    def test_permissive_mode_multiple_high_severity_tools(self):
        """Test PERMISSIVE mode with multiple HIGH severity tools."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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
                    ) as mock_emit:
                        # Should not raise exception
                        enforcer.enforce(
                            tool_name=tool_name,
                            tool_input={"path": "file.txt"},
                            context=[],
                            session_id="test-session-123",
                        )

                        # Verify logging and event emission were NOT called
                        mock_log.assert_not_called()
                        mock_emit.assert_not_called()


class TestPermissiveModeBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_default_config_is_permissive(self):
        """Test that default configuration is PERMISSIVE mode."""
        with patch("divineos.clarity_enforcement.enforcer.get_clarity_config") as mock_get_config:
            mock_config = ClarityConfig(
                enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
            mock_get_config.return_value = mock_config

            enforcer = ClarityEnforcer()

            assert enforcer.config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE

    def test_existing_code_continues_to_work(self):
        """Test that existing code continues to work without modification."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        # Simulate existing code that calls enforce without expecting exceptions
        violation = ClarityViolation(
            tool_name="fsWrite",
            tool_input={"path": "file.txt", "text": "content"},
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
                        tool_input={"path": "file.txt", "text": "content"},
                        context=[],
                        session_id="test-session-123",
                    )
                    assert result is None
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()

    def test_permissive_mode_with_log_violations_disabled(self):
        """Test PERMISSIVE mode with log_violations disabled."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
            violation_severity_threshold="medium",
            log_violations=False,  # Disabled
            emit_events=False,
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
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    # Should not raise exception
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify logging and event emission were NOT called
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()

    def test_permissive_mode_with_emit_events_disabled(self):
        """Test PERMISSIVE mode with emit_events disabled."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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
            with patch("divineos.clarity_enforcement.enforcer.log_clarity_violation") as mock_log:
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    # Should not raise exception
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id="test-session-123",
                    )

                    # Verify logging and event emission were NOT called
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()


class TestPermissiveModeEnforceFunction:
    """Test the module-level enforce_clarity function."""

    def test_enforce_clarity_function_with_permissive_mode(self):
        """Test enforce_clarity function with PERMISSIVE mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    # Should not raise exception
                    enforce_clarity(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id="test-session-123",
                        config=config,
                    )

                    # Verify logging and event emission were NOT called
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()

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
                enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
                violation_severity_threshold="medium",
                log_violations=True,
                emit_events=True,
            )
            mock_get_config.return_value = mock_config

            with patch(
                "divineos.clarity_enforcement.enforcer.detect_clarity_violation",
                return_value=violation,
            ):
                with patch(
                    "divineos.clarity_enforcement.enforcer.log_clarity_violation"
                ) as mock_log:
                    with patch(
                        "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                    ) as mock_emit:
                        # Should not raise exception
                        enforce_clarity(
                            tool_name="deleteFile",
                            tool_input={"path": "file.txt"},
                            context=[],
                            session_id="test-session-123",
                        )

                        # Verify logging and event emission were NOT called
                        mock_log.assert_not_called()
                        mock_emit.assert_not_called()


class TestPermissiveModeContextHandling:
    """Test that context is properly handled in PERMISSIVE mode."""

    def test_context_not_captured_in_permissive_mode(self):
        """Test that context is not captured/logged in PERMISSIVE mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=context,
                        session_id="test-session-123",
                    )

                    # Verify logging and event emission were NOT called
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()

    def test_session_id_not_logged_in_permissive_mode(self):
        """Test that session_id is not logged in PERMISSIVE mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
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
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id=session_id,
                    )

                    # Verify logging and event emission were NOT called
                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()


class TestPermissiveModeConfigurationLoading:
    """Test configuration loading defaults to PERMISSIVE."""

    def test_config_load_defaults_to_permissive(self):
        """Test that ClarityConfig.load() defaults to PERMISSIVE."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("pathlib.Path.home") as mock_home:
                # Create a mock Path object that doesn't exist
                mock_path = Mock()
                mock_path.exists.return_value = False
                mock_home.return_value = mock_path

                # Mock the / operator to return the same mock path
                mock_path.__truediv__ = Mock(return_value=mock_path)

                config = ClarityConfig.load()

                assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE

    def test_config_from_mode_string_permissive(self):
        """Test creating config from PERMISSIVE mode string."""
        config = ClarityConfig._from_mode_string("PERMISSIVE")

        assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE

    def test_config_from_mode_string_lowercase_permissive(self):
        """Test creating config from lowercase permissive mode string."""
        config = ClarityConfig._from_mode_string("permissive")

        assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE

    def test_config_from_dict_defaults_to_permissive(self):
        """Test creating config from dict without enforcement_mode defaults to PERMISSIVE."""
        config = ClarityConfig._from_dict({})

        assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE

    def test_config_from_dict_with_permissive_mode(self):
        """Test creating config from dict with PERMISSIVE mode."""
        config = ClarityConfig._from_dict({"enforcement_mode": "PERMISSIVE"})

        assert config.enforcement_mode == ClarityEnforcementMode.PERMISSIVE


class TestPermissiveModeMultipleViolations:
    """Test PERMISSIVE mode with multiple violations in sequence."""

    def test_multiple_violations_not_logged(self):
        """Test that multiple violations are not logged in PERMISSIVE mode."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        tools = ["deleteFile", "fsWrite", "fsAppend", "semanticRename", "smartRelocate"]

        for tool_name in tools:
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
                    ) as mock_emit:
                        # Should not raise exception
                        enforcer.enforce(
                            tool_name=tool_name,
                            tool_input={"path": "file.txt"},
                            context=[],
                            session_id="test-session-123",
                        )

                        # Verify logging and event emission were NOT called
                        mock_log.assert_not_called()
                        mock_emit.assert_not_called()

    def test_mixed_explained_and_unexplained_calls(self):
        """Test PERMISSIVE mode with mix of explained and unexplained calls."""
        config = ClarityConfig(
            enforcement_mode=ClarityEnforcementMode.PERMISSIVE,
            violation_severity_threshold="medium",
            log_violations=True,
            emit_events=True,
        )
        enforcer = ClarityEnforcer(config)

        # First call: unexplained
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
                with patch(
                    "divineos.clarity_enforcement.enforcer.emit_clarity_violation_event"
                ) as mock_emit:
                    enforcer.enforce(
                        tool_name="deleteFile",
                        tool_input={"path": "file.txt"},
                        context=[],
                        session_id="test-session-123",
                    )

                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()

        # Second call: explained
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

                    mock_log.assert_not_called()
                    mock_emit.assert_not_called()
