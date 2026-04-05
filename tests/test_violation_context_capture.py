"""Tests for violation context capture in clarity enforcement.

Validates that violations capture all required context:
- Preceding messages (last 5)
- Tool name and input parameters
- Timestamp and session_id
- User role and agent name
- Proper formatting and serialization
"""

from datetime import datetime, timezone
from divineos.clarity_enforcement.violation_detector import (
    ViolationDetector,
    ClarityViolation,
    ViolationSeverity,
    detect_clarity_violation,
)


class TestViolationContextCapture:
    """Test that violations capture all required context."""

    def test_capture_preceding_messages_last_five(self):
        """Test that last 5 preceding messages are captured."""
        detector = ViolationDetector()
        context = [
            "Message 1",
            "Message 2",
            "Message 3",
            "Message 4",
            "Message 5",
            "Message 6",
            "Message 7",
        ]

        violation = detector.detect_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=context,
            session_id="session-123",
        )

        assert violation is not None
        # Should capture last 5 messages
        assert len(violation.context) == 5
        assert violation.context == [
            "Message 3",
            "Message 4",
            "Message 5",
            "Message 6",
            "Message 7",
        ]

    def test_capture_fewer_than_five_messages(self):
        """Test that fewer than 5 messages are captured as-is."""
        detector = ViolationDetector()
        context = ["Message 1", "Message 2", "Message 3"]

        violation = detector.detect_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=context,
            session_id="session-123",
        )

        assert violation is not None
        assert len(violation.context) == 3
        assert violation.context == context

    def test_capture_empty_context(self):
        """Test that empty context is handled correctly."""
        detector = ViolationDetector()
        context = []

        violation = detector.detect_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=context,
            session_id="session-123",
        )

        assert violation is not None
        assert violation.context == []

    def test_capture_tool_name_and_input(self):
        """Test that tool name and input parameters are captured."""
        detector = ViolationDetector()
        tool_name = "deleteFile"
        tool_input = {"path": "file.py"}
        context = ["some random context without explanation"]

        violation = detector.detect_violation(
            tool_name=tool_name,
            tool_input=tool_input,
            context=context,
            session_id="session-123",
        )

        assert violation is not None
        assert violation.tool_name == tool_name
        assert violation.tool_input == tool_input

    def test_capture_timestamp_iso_format(self):
        """Test that timestamp is captured in ISO format."""
        detector = ViolationDetector()
        before = datetime.now(timezone.utc).isoformat()

        violation = detector.detect_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=["context"],
            session_id="session-123",
        )

        after = datetime.now(timezone.utc).isoformat()

        assert violation is not None
        # Timestamp should be in ISO format (YYYY-MM-DDTHH:MM:SS.ffffff)
        assert "T" in violation.timestamp
        # Should contain date and time components
        parts = violation.timestamp.split("T")
        assert len(parts) == 2
        assert "-" in parts[0]  # Date part
        assert ":" in parts[1]  # Time part
        # Timestamp should be between before and after
        assert before <= violation.timestamp <= after

    def test_capture_session_id(self):
        """Test that session_id is captured."""
        detector = ViolationDetector()
        session_id = "session-abc-123"

        violation = detector.detect_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=["context"],
            session_id=session_id,
        )

        assert violation is not None
        assert violation.session_id == session_id

    def test_capture_user_role(self):
        """Test that user role is captured."""
        detector = ViolationDetector()

        violation = detector.detect_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=["context"],
            session_id="session-123",
            user_role="admin",
        )

        assert violation is not None
        assert violation.user_role == "admin"

    def test_capture_user_role_default(self):
        """Test that user role defaults to 'user'."""
        detector = ViolationDetector()

        violation = detector.detect_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=["context"],
            session_id="session-123",
        )

        assert violation is not None
        assert violation.user_role == "user"

    def test_capture_agent_name(self):
        """Test that agent name is captured."""
        detector = ViolationDetector()

        violation = detector.detect_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=["context"],
            session_id="session-123",
            agent_name="my-agent",
        )

        assert violation is not None
        assert violation.agent_name == "my-agent"

    def test_capture_agent_name_default(self):
        """Test that agent name defaults to 'agent'."""
        detector = ViolationDetector()

        violation = detector.detect_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=["context"],
            session_id="session-123",
        )

        assert violation is not None
        assert violation.agent_name == "agent"

    def test_capture_severity(self):
        """Test that violation severity is captured."""
        detector = ViolationDetector()

        # HIGH severity tool
        violation = detector.detect_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=["context"],
            session_id="session-123",
        )

        assert violation is not None
        assert violation.severity == ViolationSeverity.HIGH

    def test_capture_all_context_together(self):
        """Test that all context is captured together."""
        detector = ViolationDetector()
        context = ["msg1", "msg2", "msg3", "msg4", "msg5", "msg6"]
        tool_name = "fsWrite"
        tool_input = {"path": "file.py", "text": "code"}
        session_id = "session-xyz"
        user_role = "developer"
        agent_name = "code-agent"

        violation = detector.detect_violation(
            tool_name=tool_name,
            tool_input=tool_input,
            context=context,
            session_id=session_id,
            user_role=user_role,
            agent_name=agent_name,
        )

        assert violation is not None
        assert violation.tool_name == tool_name
        assert violation.tool_input == tool_input
        assert len(violation.context) == 5  # Last 5 messages
        assert violation.session_id == session_id
        assert violation.user_role == user_role
        assert violation.agent_name == agent_name
        assert violation.severity == ViolationSeverity.HIGH  # fsWrite is HIGH severity


class TestViolationContextSerialization:
    """Test that violation context is properly serializable."""

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict includes all context fields."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            severity=ViolationSeverity.HIGH,
            context=["msg1", "msg2"],
            timestamp="2024-01-01T12:00:00",
            session_id="session-123",
            user_role="admin",
            agent_name="my-agent",
        )

        violation_dict = violation.to_dict()

        assert violation_dict["tool_name"] == "deleteFile"
        assert violation_dict["tool_input"] == {"path": "test.txt"}
        assert violation_dict["severity"] == "HIGH"
        assert violation_dict["context"] == ["msg1", "msg2"]
        assert violation_dict["timestamp"] == "2024-01-01T12:00:00"
        assert violation_dict["session_id"] == "session-123"
        assert violation_dict["user_role"] == "admin"
        assert violation_dict["agent_name"] == "my-agent"

    def test_to_dict_preserves_context_order(self):
        """Test that to_dict preserves context message order."""
        context = ["first", "second", "third", "fourth", "fifth"]
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            severity=ViolationSeverity.HIGH,
            context=context,
        )

        violation_dict = violation.to_dict()

        assert violation_dict["context"] == context

    def test_to_dict_handles_complex_tool_input(self):
        """Test that to_dict handles complex tool input."""
        tool_input = {
            "path": "file.py",
            "nested": {"key": "value", "list": [1, 2, 3]},
            "number": 42,
            "boolean": True,
        }
        violation = ClarityViolation(
            tool_name="fsWrite",
            tool_input=tool_input,
            severity=ViolationSeverity.MEDIUM,
        )

        violation_dict = violation.to_dict()

        assert violation_dict["tool_input"] == tool_input

    def test_to_dict_severity_as_string(self):
        """Test that severity is serialized as string."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            severity=ViolationSeverity.HIGH,
        )

        violation_dict = violation.to_dict()

        assert isinstance(violation_dict["severity"], str)
        assert violation_dict["severity"] == "HIGH"


class TestViolationContextImmutability:
    """Test that violation context is immutable."""

    def test_violation_is_dataclass(self):
        """Test that ClarityViolation is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(ClarityViolation)

    def test_violation_context_is_list(self):
        """Test that context is stored as a list."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            severity=ViolationSeverity.HIGH,
            context=["msg1", "msg2"],
        )

        assert isinstance(violation.context, list)

    def test_violation_tool_input_is_dict(self):
        """Test that tool_input is stored as a dict."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            severity=ViolationSeverity.HIGH,
        )

        assert isinstance(violation.tool_input, dict)


class TestViolationContextQueryability:
    """Test that violation context is queryable."""

    def test_access_context_fields(self):
        """Test that all context fields are accessible."""
        violation = ClarityViolation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            severity=ViolationSeverity.HIGH,
            context=["msg1", "msg2"],
            timestamp="2024-01-01T12:00:00",
            session_id="session-123",
            user_role="admin",
            agent_name="my-agent",
        )

        # All fields should be accessible
        assert violation.tool_name
        assert violation.tool_input
        assert violation.severity
        assert violation.context
        assert violation.timestamp
        assert violation.session_id
        assert violation.user_role
        assert violation.agent_name

    def test_query_by_session_id(self):
        """Test that violations can be queried by session_id."""
        detector = ViolationDetector()
        session_id = "session-query-test"

        violation = detector.detect_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=["context"],
            session_id=session_id,
        )

        assert violation is not None
        assert violation.session_id == session_id

    def test_query_by_tool_name(self):
        """Test that violations can be queried by tool_name."""
        detector = ViolationDetector()
        tool_name = "fsWrite"

        violation = detector.detect_violation(
            tool_name=tool_name,
            tool_input={"path": "test.txt"},
            context=["context"],
            session_id="session-123",
        )

        assert violation is not None
        assert violation.tool_name == tool_name

    def test_query_by_severity(self):
        """Test that violations can be queried by severity."""
        detector = ViolationDetector()

        violation = detector.detect_violation(
            tool_name="deleteFile",  # HIGH severity
            tool_input={"path": "test.txt"},
            context=["context"],
            session_id="session-123",
        )

        assert violation is not None
        assert violation.severity == ViolationSeverity.HIGH


class TestDetectClarityViolationFunction:
    """Test the module-level detect_clarity_violation function."""

    def test_function_captures_context(self):
        """Test that the function captures context."""
        context = ["msg1", "msg2", "msg3"]
        violation = detect_clarity_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=context,
            session_id="session-123",
        )

        assert violation is not None
        assert violation.context == context

    def test_function_returns_none_for_explained_calls(self):
        """Test that function returns None for explained calls."""
        context = ["I need to read the file"]
        violation = detect_clarity_violation(
            tool_name="readFile",
            tool_input={"path": "test.txt"},
            context=context,
            session_id="session-123",
        )

        # readFile with "read" in context should be explained
        assert violation is None

    def test_function_returns_violation_for_unexplained_calls(self):
        """Test that function returns violation for unexplained calls."""
        context = ["some random context"]
        violation = detect_clarity_violation(
            tool_name="deleteFile",
            tool_input={"path": "test.txt"},
            context=context,
            session_id="session-123",
        )

        # deleteFile without clear explanation should be a violation
        assert violation is not None
        assert violation.tool_name == "deleteFile"
