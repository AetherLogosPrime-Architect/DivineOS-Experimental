"""
Test that TOOL_CALL and TOOL_RESULT events are properly captured.

This test verifies that when tools are executed, both TOOL_CALL and TOOL_RESULT
events are emitted to the ledger with correct data.
"""

from divineos.event.event_emission import emit_tool_call, emit_tool_result
from divineos.core.ledger import count_events


def test_tool_call_event_can_be_emitted():
    """Test that TOOL_CALL events can be emitted."""
    tool_name = "readFile"
    tool_input = {"path": "test.txt"}
    tool_use_id = "test-tool-use-123"

    # Get initial count
    initial_count = count_events()

    # Emit TOOL_CALL
    event_id = emit_tool_call(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_use_id=tool_use_id,
    )

    assert event_id is not None
    assert len(event_id) > 0

    # Verify count increased
    new_count = count_events()
    assert new_count["total"] > initial_count["total"]


def test_tool_result_event_can_be_emitted():
    """Test that TOOL_RESULT events can be emitted."""
    tool_name = "readFile"
    result = "file contents here"
    duration_ms = 150
    tool_use_id = "test-tool-use-456"

    # Get initial count
    initial_count = count_events()

    # Emit TOOL_RESULT
    event_id = emit_tool_result(
        tool_name=tool_name,
        result=result,
        duration_ms=duration_ms,
        tool_use_id=tool_use_id,
    )

    assert event_id is not None
    assert len(event_id) > 0

    # Verify count increased
    new_count = count_events()
    assert new_count["total"] > initial_count["total"]


def test_tool_call_and_result_can_be_emitted_together():
    """Test that TOOL_CALL and TOOL_RESULT can both be emitted."""
    tool_name = "executePwsh"
    tool_input = {"command": "echo hello"}
    tool_use_id = "test-tool-use-789"
    result = "hello"
    duration_ms = 100

    # Get initial count
    initial_count = count_events()

    # Emit TOOL_CALL
    call_event_id = emit_tool_call(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_use_id=tool_use_id,
    )

    # Emit TOOL_RESULT
    result_event_id = emit_tool_result(
        tool_name=tool_name,
        result=result,
        duration_ms=duration_ms,
        tool_use_id=tool_use_id,
    )

    assert call_event_id is not None
    assert result_event_id is not None

    # Verify count increased by 2
    new_count = count_events()
    assert new_count["total"] >= initial_count["total"] + 2


def test_tool_result_with_failure_can_be_emitted():
    """Test that TOOL_RESULT with failure can be emitted."""
    tool_name = "readFile"
    error_message = "File not found"
    duration_ms = 50
    tool_use_id = "test-tool-use-fail"

    # Get initial count
    initial_count = count_events()

    # Emit TOOL_RESULT with failure
    event_id = emit_tool_result(
        tool_name=tool_name,
        result=error_message,  # Must have non-empty result
        duration_ms=duration_ms,
        failed=True,
        error_message=error_message,
        tool_use_id=tool_use_id,
    )

    assert event_id is not None

    # Verify count increased
    new_count = count_events()
    assert new_count["total"] > initial_count["total"]
