"""
Unit tests for error handling and recovery in enforcement system.

Tests cover:
- Event emission failures
- Session file corruption
- Permission errors
- Ledger unavailability
- Tool execution failures
- Signal handling errors
- Cleanup on exit errors
"""

import pytest
from unittest.mock import patch, MagicMock

from divineos.core.enforcement import (
    setup_cli_enforcement,
    capture_user_input,
    handle_cli_error,
)
from divineos.core.session_manager import (
    initialize_session,
    end_session,
    clear_session,
    _read_session_file,
    _write_session_file,
    _clear_session_file,
)
from divineos.core.tool_wrapper import wrap_tool_execution
from divineos.core.loop_prevention import mark_internal_operation


class TestEnforcementErrorHandling:
    """Test error handling in enforcement.py"""

    def test_setup_cli_enforcement_with_session_init_failure(self):
        """Test setup_cli_enforcement continues when session init fails"""
        # Reset global state
        import divineos.core.enforcement as enf_module

        enf_module._signal_handlers_setup = False
        enf_module._session_initialized = False

        with patch("divineos.core.enforcement.initialize_session") as mock_init:
            mock_init.side_effect = RuntimeError("Session init failed")
            with patch("divineos.core.enforcement._is_test_environment", return_value=False):
                # Should not raise, should continue
                setup_cli_enforcement()

                # Verify it was called
                mock_init.assert_called_once()

    def test_setup_cli_enforcement_with_signal_handler_failure(self):
        """Test setup_cli_enforcement continues when signal setup fails"""
        # Reset global state
        import divineos.core.enforcement as enf_module

        enf_module._signal_handlers_setup = False
        enf_module._session_initialized = False

        with patch("divineos.core.enforcement.initialize_session"):
            with patch("divineos.core.enforcement._setup_signal_handlers") as mock_signal:
                mock_signal.side_effect = RuntimeError("Signal setup failed")
                with patch("divineos.core.enforcement._is_test_environment", return_value=False):
                    # Should not raise, should continue
                    setup_cli_enforcement()

                    # Verify it was called
                    mock_signal.assert_called_once()

    def test_capture_user_input_with_event_emission_failure(self):
        """Test capture_user_input continues when event emission fails"""
        with patch("divineos.core.enforcement.emit_user_input") as mock_emit:
            mock_emit.side_effect = ValueError("Event validation failed")

            # Should not raise, should return input
            result = capture_user_input(["test", "command"])

            assert result == "test command"
            mock_emit.assert_called_once()

    def test_capture_user_input_with_unexpected_error(self):
        """Test capture_user_input handles unexpected errors"""
        with patch("divineos.core.enforcement.emit_user_input") as mock_emit:
            mock_emit.side_effect = Exception("Unexpected error")

            # Should not raise, should return input
            result = capture_user_input(["test", "command"])

            assert result == "test command"

    def test_capture_user_input_with_empty_args(self):
        """Test capture_user_input handles empty arguments"""
        with patch("divineos.core.enforcement.emit_user_input"):
            result = capture_user_input([])

            assert result == ""

    def test_handle_cli_error_with_exception(self):
        """Test handle_cli_error handles exceptions gracefully"""
        error = RuntimeError("Test error")

        # Should not raise
        handle_cli_error(error)


class TestSessionManagerErrorHandling:
    """Test error handling in session_manager.py"""

    def test_read_session_file_with_permission_error(self):
        """Test _read_session_file handles permission errors"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text") as mock_read:
                mock_read.side_effect = PermissionError("Permission denied")

                result = _read_session_file()

                assert result is None

    def test_read_session_file_with_file_not_found(self):
        """Test _read_session_file handles file not found"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text") as mock_read:
                mock_read.side_effect = FileNotFoundError("File not found")

                result = _read_session_file()

                assert result is None

    def test_read_session_file_with_unexpected_error(self):
        """Test _read_session_file handles unexpected errors"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text") as mock_read:
                mock_read.side_effect = Exception("Unexpected error")

                result = _read_session_file()

                assert result is None

    def test_write_session_file_with_permission_error(self):
        """Test _write_session_file handles permission errors"""
        with patch("pathlib.Path.parent") as mock_parent:
            mock_parent.mkdir.side_effect = PermissionError("Permission denied")

            result = _write_session_file("test-session-id")

            assert result is False

    def test_write_session_file_with_os_error(self):
        """Test _write_session_file handles OS errors"""
        with patch("pathlib.Path.parent") as mock_parent:
            mock_parent.mkdir.side_effect = OSError("OS error")

            result = _write_session_file("test-session-id")

            assert result is False

    def test_write_session_file_with_unexpected_error(self):
        """Test _write_session_file handles unexpected errors"""
        with patch("pathlib.Path.parent") as mock_parent:
            mock_parent.mkdir.side_effect = Exception("Unexpected error")

            result = _write_session_file("test-session-id")

            assert result is False

    def test_clear_session_file_with_permission_error(self):
        """Test _clear_session_file handles permission errors"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.unlink") as mock_unlink:
                mock_unlink.side_effect = PermissionError("Permission denied")

                result = _clear_session_file()

                assert result is False

    def test_clear_session_file_with_file_not_found(self):
        """Test _clear_session_file handles file not found"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.unlink") as mock_unlink:
                mock_unlink.side_effect = FileNotFoundError("File not found")

                result = _clear_session_file()

                assert result is True

    def test_initialize_session_with_write_failure(self):
        """Test initialize_session continues when write fails"""
        with patch("divineos.core.session_manager._read_session_file", return_value=None):
            with patch("divineos.core.session_manager._write_session_file", return_value=False):
                with patch("os.environ", {}):
                    result = initialize_session()

                    # Should still return a valid session_id
                    assert result is not None
                    assert len(result) > 0

    def test_initialize_session_with_env_var_failure(self):
        """Test initialize_session continues when env var set fails"""
        with patch("divineos.core.session_manager._read_session_file", return_value=None):
            with patch("divineos.core.session_manager._write_session_file", return_value=True):
                # Mock os.environ as a dict-like object that raises on setitem
                mock_env = MagicMock()
                mock_env.get.return_value = None
                mock_env.__setitem__.side_effect = Exception("Env var error")

                with patch("os.environ", mock_env):
                    # Should not raise
                    result = initialize_session()

                    # Should still return a valid session_id
                    assert result is not None

    def test_end_session_with_event_emission_failure(self):
        """Test end_session continues when event emission fails"""
        with patch("divineos.core.session_manager.get_current_session_id", return_value="test-id"):
            with patch("divineos.core.session_manager.clear_session"):
                # Import and patch the emit_session_end function

                with patch("divineos.event.event_emission.emit_session_end") as mock_emit:
                    mock_emit.side_effect = ValueError("Event validation failed")

                    # Should not raise
                    result = end_session()

                    # Should return empty string on error
                    assert result == ""

    def test_end_session_with_clear_failure(self):
        """Test end_session continues even if clear_session fails"""
        with patch("divineos.core.session_manager.get_current_session_id", return_value="test-id"):
            with patch("divineos.core.session_manager.clear_session") as mock_clear:
                mock_clear.side_effect = Exception("Clear failed")

                # Import and patch the emit_session_end function

                with patch(
                    "divineos.event.event_emission.emit_session_end", return_value="event-id"
                ):
                    # Should raise the exception from clear_session
                    with pytest.raises(Exception, match="Clear failed"):
                        end_session()

    def test_clear_session_with_file_error(self):
        """Test clear_session continues when file clear fails"""
        with patch("divineos.core.session_manager._clear_session_file") as mock_clear:
            mock_clear.side_effect = Exception("File clear failed")

            with patch("os.environ", {"DIVINEOS_SESSION_ID": "test-id"}):
                # Should not raise
                clear_session()


class TestToolWrapperErrorHandling:
    """Test error handling in tool_wrapper.py"""

    def test_wrap_tool_execution_with_tool_call_event_failure(self):
        """Test tool wrapper continues when TOOL_CALL event fails"""

        def test_tool():
            return "result"

        with patch("divineos.core.tool_wrapper.should_capture_tool", return_value=True):
            with patch("divineos.core.tool_wrapper.emit_tool_call") as mock_emit:
                mock_emit.side_effect = ValueError("Event validation failed")

                with patch("divineos.core.tool_wrapper.emit_tool_result"):
                    wrapped = wrap_tool_execution("test_tool", test_tool)

                    # Should not raise, should execute tool
                    result = wrapped()

                    assert result == "result"

    def test_wrap_tool_execution_with_tool_result_event_failure(self):
        """Test tool wrapper continues when TOOL_RESULT event fails"""

        def test_tool():
            return "result"

        with patch("divineos.core.tool_wrapper.should_capture_tool", return_value=True):
            with patch("divineos.core.tool_wrapper.emit_tool_call"):
                with patch("divineos.core.tool_wrapper.emit_tool_result") as mock_emit:
                    mock_emit.side_effect = ValueError("Event validation failed")

                    wrapped = wrap_tool_execution("test_tool", test_tool)

                    # Should not raise, should execute tool
                    result = wrapped()

                    assert result == "result"

    def test_wrap_tool_execution_with_tool_failure(self):
        """Test tool wrapper captures tool failures"""

        def failing_tool():
            raise RuntimeError("Tool failed")

        with patch("divineos.core.tool_wrapper.should_capture_tool", return_value=True):
            with patch("divineos.core.tool_wrapper.emit_tool_call"):
                with patch("divineos.core.tool_wrapper.emit_tool_result") as mock_emit:
                    wrapped = wrap_tool_execution("test_tool", failing_tool)

                    # Should raise the original exception
                    with pytest.raises(RuntimeError, match="Tool failed"):
                        wrapped()

                    # Should have emitted TOOL_RESULT with failed=True
                    assert mock_emit.called
                    call_kwargs = mock_emit.call_args[1]
                    assert call_kwargs["failed"] is True
                    assert "Tool failed" in call_kwargs["error_message"]

    def test_wrap_tool_execution_with_tool_failure_and_event_failure(self):
        """Test tool wrapper handles both tool and event failures"""

        def failing_tool():
            raise RuntimeError("Tool failed")

        with patch("divineos.core.tool_wrapper.should_capture_tool", return_value=True):
            with patch("divineos.core.tool_wrapper.emit_tool_call"):
                with patch("divineos.core.tool_wrapper.emit_tool_result") as mock_emit:
                    mock_emit.side_effect = ValueError("Event validation failed")

                    wrapped = wrap_tool_execution("test_tool", failing_tool)

                    # Should raise the original exception
                    with pytest.raises(RuntimeError, match="Tool failed"):
                        wrapped()

    def test_wrap_tool_execution_with_internal_tool(self):
        """Test tool wrapper skips internal tools"""

        def test_tool():
            return "result"

        with patch("divineos.core.tool_wrapper.should_capture_tool", return_value=False):
            wrapped = wrap_tool_execution("internal_tool", test_tool)

            # Should execute tool without event capture
            result = wrapped()

            assert result == "result"


class TestLoopPreventionErrorHandling:
    """Test error handling in loop prevention"""

    def test_mark_internal_operation_with_exception(self):
        """Test mark_internal_operation handles exceptions"""
        from divineos.core.loop_prevention import is_internal_operation

        with mark_internal_operation():
            assert is_internal_operation() is True

            # Raise exception inside context
            try:
                raise RuntimeError("Test error")
            except RuntimeError:
                pass

        # Should be reset after context
        assert is_internal_operation() is False

    def test_mark_internal_operation_nested(self):
        """Test mark_internal_operation handles nesting"""
        from divineos.core.loop_prevention import is_internal_operation

        assert is_internal_operation() is False

        with mark_internal_operation():
            assert is_internal_operation() is True

            with mark_internal_operation():
                assert is_internal_operation() is True

            assert is_internal_operation() is True

        assert is_internal_operation() is False


class TestErrorRecovery:
    """Test error recovery mechanisms"""

    def test_session_recovery_after_file_corruption(self):
        """Test session recovery when file is corrupted"""
        with patch("divineos.core.session_manager._read_session_file", return_value=None):
            with patch("divineos.core.session_manager._write_session_file", return_value=False):
                # First initialization should generate new session_id
                session_id_1 = initialize_session()

                # Clear session
                clear_session()

                # Second initialization should generate new session_id
                session_id_2 = initialize_session()

                # Should be different (new session)
                assert session_id_1 != session_id_2

    def test_tool_execution_continues_after_event_failure(self):
        """Test tool execution continues after event capture failure"""
        call_count = 0

        def test_tool():
            nonlocal call_count
            call_count += 1
            return "result"

        with patch("divineos.core.tool_wrapper.should_capture_tool", return_value=True):
            with patch("divineos.core.tool_wrapper.emit_tool_call") as mock_call:
                with patch("divineos.core.tool_wrapper.emit_tool_result") as mock_result:
                    # First call fails
                    mock_call.side_effect = [ValueError("Event failed"), None]
                    mock_result.side_effect = [ValueError("Event failed"), None]

                    wrapped = wrap_tool_execution("test_tool", test_tool)

                    # First execution should still work
                    result_1 = wrapped()
                    assert result_1 == "result"
                    assert call_count == 1

                    # Second execution should also work
                    result_2 = wrapped()
                    assert result_2 == "result"
                    assert call_count == 2
