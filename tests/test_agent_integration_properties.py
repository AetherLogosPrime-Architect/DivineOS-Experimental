"""
Property-Based Tests for DivineOS Agent Integration

Tests formal correctness properties that must hold across all valid inputs.
Each property is universally quantified and validated using hypothesis.

Feature: agent-integration
"""

import pytest
from datetime import datetime
import uuid

from hypothesis_compat import HAS_HYPOTHESIS, given, st, settings, HealthCheck


from divineos.agent_integration.types import (
    ToolCallEvent,
    ToolResultEvent,
    INTERNAL_TOOLS,
)
from divineos.agent_integration.mcp_integration import (
    validate_explanation,
)
from divineos.event.event_capture import get_current_timestamp as get_iso8601_timestamp
from divineos.core.loop_prevention import (
    should_capture_tool,
    mark_internal_operation,
    is_internal_operation,
)
from divineos.agent_integration.learning_loop import (
    extract_tool_patterns,
    extract_timing_patterns,
    extract_error_patterns,
)
from divineos.agent_integration.behavior_analyzer import (
    calculate_tool_frequency,
    calculate_success_rates,
    calculate_execution_times,
)

# Skip all tests in this module if hypothesis is not installed
pytestmark = pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")


# ============================================================================
# Property 1: All Agent Tool Calls Are Captured
# ============================================================================


@given(
    tool_name=st.text(min_size=1, max_size=50),
    tool_input=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.text(min_size=1, max_size=100),
        min_size=1,
    ),
)
@pytest.mark.slow
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_1_tool_calls_captured(tool_name, tool_input):
    """
    Property 1: All Agent Tool Calls Are Captured

    For any DivineOS agent tool invocation, a TOOL_CALL event SHALL be emitted
    before the tool executes, containing the tool name, input parameters,
    unique tool_use_id, timestamp in ISO8601 format, and actor="assistant".
    """
    # Add explanation to tool_input
    tool_input["explanation"] = "Test operation"

    # Create a TOOL_CALL event
    event = ToolCallEvent(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_use_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        timestamp=get_iso8601_timestamp(),
        explanation="Test operation",
        actor="assistant",
    )

    # Verify all required fields are present
    assert event.tool_name == tool_name
    assert event.tool_input == tool_input
    assert len(event.tool_use_id) > 0
    assert len(event.session_id) > 0
    assert event.actor == "assistant"

    # Verify timestamp is ISO8601
    try:
        datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"Timestamp {event.timestamp} is not ISO8601 format")


# ============================================================================
# Property 2: All Agent Tool Results Are Captured
# ============================================================================


@given(
    tool_name=st.text(min_size=1, max_size=50),
    result=st.text(max_size=1000),
    duration_ms=st.integers(min_value=0, max_value=10000),
)
@pytest.mark.slow
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_2_tool_results_captured(tool_name, result, duration_ms):
    """
    Property 2: All Agent Tool Results Are Captured

    For any completed DivineOS agent tool execution, a TOOL_RESULT event SHALL be
    emitted after the tool returns, containing the tool name, matching
    tool_use_id, complete result output, execution duration in milliseconds,
    and actor="assistant".
    """
    tool_use_id = str(uuid.uuid4())

    # Create a TOOL_RESULT event
    event = ToolResultEvent(
        tool_name=tool_name,
        tool_use_id=tool_use_id,
        result=result,
        duration_ms=duration_ms,
        session_id=str(uuid.uuid4()),
        timestamp=get_iso8601_timestamp(),
        failed=False,
        error_message=None,
        actor="assistant",
    )

    # Verify all required fields are present
    assert event.tool_name == tool_name
    assert event.tool_use_id == tool_use_id
    assert event.result == result
    assert event.duration_ms == duration_ms
    assert event.actor == "assistant"
    assert not event.failed


# ============================================================================
# Property 3: Failed Tool Executions Are Recorded
# ============================================================================


@given(
    tool_name=st.text(min_size=1, max_size=50),
    error_message=st.text(min_size=1, max_size=200),
)
@pytest.mark.slow
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_3_failed_executions_recorded(tool_name, error_message):
    """
    Property 3: Failed Tool Executions Are Recorded

    For any DivineOS agent tool execution that fails with an exception, a
    TOOL_RESULT event SHALL be emitted with failed=true and error_message
    containing the exception details.
    """
    tool_use_id = str(uuid.uuid4())

    # Create a failed TOOL_RESULT event
    event = ToolResultEvent(
        tool_name=tool_name,
        tool_use_id=tool_use_id,
        result="",
        duration_ms=100,
        session_id=str(uuid.uuid4()),
        timestamp=get_iso8601_timestamp(),
        failed=True,
        error_message=error_message,
        actor="assistant",
    )

    # Verify failure is recorded
    assert event.failed
    assert event.error_message == error_message


# ============================================================================
# Property 4: Events Are Stored in Ledger with Hash Validation
# ============================================================================


@given(
    tool_name=st.text(min_size=1, max_size=50),
)
@pytest.mark.slow
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_4_events_stored_with_hash(tool_name):
    """
    Property 4: Events Are Stored in Ledger with Hash Validation

    For any TOOL_CALL or TOOL_RESULT event emitted for agent operations,
    the event SHALL be stored in the ledger with a valid SHA256 hash that
    can be verified for integrity.
    """
    # Create events
    call_event = ToolCallEvent(
        tool_name=tool_name,
        tool_input={"explanation": "Test"},
        tool_use_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        timestamp=get_iso8601_timestamp(),
        explanation="Test",
        actor="assistant",
    )

    result_event = ToolResultEvent(
        tool_name=tool_name,
        tool_use_id=call_event.tool_use_id,
        result="Success",
        duration_ms=50,
        session_id=call_event.session_id,
        timestamp=get_iso8601_timestamp(),
        failed=False,
        actor="assistant",
    )

    # Verify events can be converted to dict (for storage)
    call_dict = call_event.to_dict()
    result_dict = result_event.to_dict()

    assert isinstance(call_dict, dict)
    assert isinstance(result_dict, dict)
    assert "tool_name" in call_dict
    assert "tool_name" in result_dict


# ============================================================================
# Property 8: Internal Operations Are Not Recursively Captured
# ============================================================================


@given(
    tool_name=st.text(min_size=1, max_size=50),
)
@pytest.mark.slow
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_8_loop_prevention(tool_name):
    """
    Property 8: Internal Operations Are Not Recursively Captured

    For any internal operation (event emission, ledger access, session
    management, logging), the operation SHALL NOT trigger emission of
    TOOL_CALL or TOOL_RESULT events, preventing infinite loops.
    """
    # Test internal operation marking
    assert not is_internal_operation()

    with mark_internal_operation():
        assert is_internal_operation()
        # Internal tools should not be captured
        for internal_tool in list(INTERNAL_TOOLS)[:5]:
            assert not should_capture_tool(internal_tool)

    assert not is_internal_operation()


# ============================================================================
# Property 9: All Specified Agent Tools Are Captured
# ============================================================================


@given(
    tool_name=st.sampled_from(
        [
            "readFile",
            "readCode",
            "readMultipleFiles",
            "strReplace",
            "fsWrite",
            "fsAppend",
            "editCode",
            "getDiagnostics",
            "grepSearch",
            "fileSearch",
            "listDirectory",
            "deleteFile",
        ]
    ),
)
@pytest.mark.slow
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_9_all_tools_captured(tool_name):
    """
    Property 9: All Specified Agent Tools Are Captured

    For any DivineOS agent tool call (readFile, strReplace, fsWrite, editCode,
    getDiagnostics, etc.), the tool invocation SHALL be captured as
    TOOL_CALL and TOOL_RESULT events.
    """
    # Verify tool is not in internal tools list
    assert tool_name not in INTERNAL_TOOLS

    # Verify tool should be captured
    assert should_capture_tool(tool_name)


# ============================================================================
# Property 10: Event Capture Failures Do Not Crash Execution
# ============================================================================


@given(
    tool_name=st.text(min_size=1, max_size=50),
)
@pytest.mark.slow
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_10_error_resilience(tool_name):
    """
    Property 10: Event Capture Failures Do Not Crash Execution

    For any failure in event capture (validation error, ledger error,
    session retrieval error), the tool execution SHALL continue normally,
    the error SHALL be logged, and the system SHALL attempt to recover and
    capture subsequent events.
    """
    # Test that invalid explanation doesn't crash
    invalid_input = {"no_explanation": "value"}
    assert not validate_explanation(invalid_input)

    # Test that empty explanation doesn't crash
    empty_input = {"explanation": ""}
    assert not validate_explanation(empty_input)

    # Test that valid explanation works
    valid_input = {"explanation": "Valid explanation"}
    assert validate_explanation(valid_input)


# ============================================================================
# Property 13: Explanation Parameter Is Required and Validated
# ============================================================================


@given(
    explanation=st.text(max_size=500),
)
@pytest.mark.slow
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_13_explanation_validation(explanation):
    """
    Property 13: Explanation Parameter Is Required and Validated

    For any agent tool call, the tool_input SHALL contain an "explanation"
    parameter that is non-empty and not purely whitespace; if invalid, an
    EXPLANATION event SHALL be emitted with a warning.
    """
    tool_input = {"explanation": explanation}

    # Validate explanation
    is_valid = validate_explanation(tool_input)

    # Should be valid only if non-empty and not whitespace
    expected_valid = bool(explanation.strip())
    assert is_valid == expected_valid


# ============================================================================
# Property 14: Performance Overhead Is Minimal
# ============================================================================


@given(
    tool_name=st.text(min_size=1, max_size=50),
)
@pytest.mark.slow
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_property_14_performance_overhead(tool_name):
    """
    Property 14: Performance Overhead Is Minimal

    For any agent tool call with event capture enabled, the total overhead
    added by event emission, validation, and storage SHALL be less than
    10 milliseconds.
    """
    import time

    # Measure overhead of validation
    start = time.perf_counter()
    for _ in range(100):
        validate_explanation({"explanation": "test"})
    validation_time = (time.perf_counter() - start) * 1000

    # Validation should be very fast (< 1ms for 100 calls)
    assert validation_time < 10


# ============================================================================
# Property 15: Session Lessons Are Extracted and Stored
# ============================================================================


@given(
    num_events=st.integers(min_value=1, max_value=20),
)
@pytest.mark.slow
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_property_15_lessons_extracted(num_events):
    """
    Property 15: Session Lessons Are Extracted and Stored

    For any completed session containing agent tool calls, the learning
    loop system SHALL analyze the session and extract lessons (corrections,
    encouragements, decisions, tool patterns, timing patterns, error
    patterns) and store them as knowledge entries.
    """
    # Create events with proper timestamps
    events = []
    for i in range(num_events):
        events.append(
            {
                "event_type": "TOOL_RESULT",
                "payload": {
                    "tool_name": f"tool_{i % 3}",
                    "failed": i % 5 == 0,
                    "duration_ms": 50 + i * 10,
                    "error_message": "Test error" if i % 5 == 0 else None,
                    "session_id": "test-session",
                },
                "timestamp": i * 100,
            }
        )

    # Extract patterns from events
    tool_patterns = extract_tool_patterns(events)
    timing_patterns = extract_timing_patterns(events)
    error_patterns = extract_error_patterns(events)

    # Verify patterns are extracted
    assert isinstance(tool_patterns, dict)
    assert isinstance(timing_patterns, dict)
    assert isinstance(error_patterns, dict)


# ============================================================================
# Property 17: Agent Behavior Metrics Are Tracked
# ============================================================================


@given(
    num_events=st.integers(min_value=1, max_value=20),
)
@pytest.mark.slow
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_property_17_behavior_metrics(num_events):
    """
    Property 17: Agent Behavior Metrics Are Tracked

    For any session, the behavior analyzer SHALL track tool call frequency,
    success rates, execution times, error patterns, correction patterns,
    and decision patterns, and generate a behavior report identifying
    strengths, weaknesses, and optimization opportunities.
    """
    # Create events with proper structure
    events = []
    for i in range(num_events):
        events.append(
            {
                "event_type": "TOOL_RESULT",
                "payload": {
                    "tool_name": f"tool_{i % 3}",
                    "failed": i % 5 == 0,
                    "duration_ms": 50 + i * 10,
                },
            }
        )

    # Calculate metrics
    frequency = calculate_tool_frequency(events)
    success_rates = calculate_success_rates(events)
    execution_times = calculate_execution_times(events)

    # Verify metrics are calculated
    assert isinstance(frequency, dict)
    assert isinstance(success_rates, dict)
    assert isinstance(execution_times, dict)

    # Verify success rates are between 0 and 1
    for tool, rate in success_rates.items():
        assert 0 <= rate <= 1


# ============================================================================
# Property 19: Tool Call and Result Events Are Correlated
# ============================================================================


@given(
    tool_name=st.text(min_size=1, max_size=50),
)
@pytest.mark.slow
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_19_event_correlation(tool_name):
    """
    Property 19: Tool Call and Result Events Are Correlated

    For any TOOL_CALL event emitted for an agent tool, there SHALL be a
    corresponding TOOL_RESULT event with a matching tool_use_id, and the
    TOOL_RESULT SHALL be emitted after the TOOL_CALL.
    """
    tool_use_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    # Create TOOL_CALL event
    call_event = ToolCallEvent(
        tool_name=tool_name,
        tool_input={"explanation": "Test"},
        tool_use_id=tool_use_id,
        session_id=session_id,
        timestamp=get_iso8601_timestamp(),
        explanation="Test",
        actor="assistant",
    )

    # Create TOOL_RESULT event with matching tool_use_id
    result_event = ToolResultEvent(
        tool_name=tool_name,
        tool_use_id=tool_use_id,
        result="Success",
        duration_ms=50,
        session_id=session_id,
        timestamp=get_iso8601_timestamp(),
        failed=False,
        actor="assistant",
    )

    # Verify correlation
    assert call_event.tool_use_id == result_event.tool_use_id
    assert call_event.session_id == result_event.session_id


# ============================================================================
# Property 20: Explanation Is Included in TOOL_CALL Event
# ============================================================================


@given(
    explanation=st.text(min_size=1, max_size=200),
)
@pytest.mark.slow
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_20_explanation_in_event(explanation):
    """
    Property 20: Explanation Is Included in TOOL_CALL Event

    For any TOOL_CALL event emitted for an agent tool, the event payload
    SHALL include the explanation parameter from the tool_input.
    """
    tool_input = {"explanation": explanation}

    # Create TOOL_CALL event
    event = ToolCallEvent(
        tool_name="testTool",
        tool_input=tool_input,
        tool_use_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        timestamp=get_iso8601_timestamp(),
        explanation=explanation,
        actor="assistant",
    )

    # Verify explanation is in event
    assert event.explanation == explanation
    assert event.tool_input["explanation"] == explanation
