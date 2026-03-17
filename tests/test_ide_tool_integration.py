"""Tests for IDE tool integration module."""

import pytest
from divineos.ledger import init_db, get_events
from divineos.consolidation import init_knowledge_table
from divineos.ide_tool_integration import (
    IDEToolExecutor,
    emit_tool_call_for_ide,
    emit_tool_result_for_ide,
    get_ide_tool_executor,
)


@pytest.fixture(autouse=True)
def setup_tests(tmp_path, monkeypatch):
    """Setup test environment with isolated ledger."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    init_db()
    init_knowledge_table()
    yield
    if test_db.exists():
        test_db.unlink()


class TestIDEToolExecutor:
    """Tests for IDEToolExecutor class."""

    def test_start_tool_execution_emits_tool_call(self):
        """Test that starting tool execution emits TOOL_CALL event."""
        executor = IDEToolExecutor()
        tool_use_id = executor.start_tool_execution("readFile", {"path": "file.py"})

        assert tool_use_id is not None

        # Verify TOOL_CALL event was emitted
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) > 0
        assert events[0]["payload"]["tool_name"] == "readFile"

    def test_end_tool_execution_emits_tool_result(self):
        """Test that ending tool execution emits TOOL_RESULT event."""
        executor = IDEToolExecutor()
        tool_use_id = executor.start_tool_execution("readFile", {"path": "file.py"})

        event_id = executor.end_tool_execution(tool_use_id, "file content here")

        assert event_id is not None

        # Verify TOOL_RESULT event was emitted
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) > 0
        assert events[0]["payload"]["tool_name"] == "readFile"
        assert events[0]["payload"]["result"] == "file content here"

    def test_execute_tool_captures_both_events(self):
        """Test that execute_tool captures both TOOL_CALL and TOOL_RESULT."""
        executor = IDEToolExecutor()

        def mock_tool(path: str) -> str:
            return f"content of {path}"

        result = executor.execute_tool("readFile", {"path": "test.py"}, mock_tool)

        assert result == "content of test.py"

        # Verify both events were emitted
        tool_calls = get_events(limit=10, event_type="TOOL_CALL")
        tool_results = get_events(limit=10, event_type="TOOL_RESULT")

        assert len(tool_calls) > 0
        assert len(tool_results) > 0

    def test_execute_tool_captures_failure(self):
        """Test that execute_tool captures failures."""
        executor = IDEToolExecutor()

        def mock_tool_fail(path: str) -> str:
            raise ValueError("File not found")

        with pytest.raises(ValueError):
            executor.execute_tool("readFile", {"path": "missing.py"}, mock_tool_fail)

        # Verify TOOL_RESULT event shows failure
        tool_results = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(tool_results) > 0
        assert tool_results[0]["payload"]["failed"] is True


class TestIDEToolIntegrationFunctions:
    """Tests for IDE tool integration functions."""

    def test_emit_tool_call_for_ide(self):
        """Test emit_tool_call_for_ide function."""
        tool_use_id = emit_tool_call_for_ide(
            "strReplace", {"path": "file.py", "oldStr": "old", "newStr": "new"}
        )

        assert tool_use_id is not None

        # Verify TOOL_CALL event
        events = get_events(limit=10, event_type="TOOL_CALL")
        assert len(events) > 0
        assert events[0]["payload"]["tool_name"] == "strReplace"

    def test_emit_tool_result_for_ide(self):
        """Test emit_tool_result_for_ide function."""
        tool_use_id = emit_tool_call_for_ide(
            "strReplace", {"path": "file.py", "oldStr": "old", "newStr": "new"}
        )

        event_id = emit_tool_result_for_ide(tool_use_id, "Replaced 1 occurrence")

        assert event_id is not None

        # Verify TOOL_RESULT event
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) > 0
        assert events[0]["payload"]["result"] == "Replaced 1 occurrence"

    def test_emit_tool_result_for_ide_with_failure(self):
        """Test emit_tool_result_for_ide with failure flag."""
        tool_use_id = emit_tool_call_for_ide("readFile", {"path": "missing.py"})

        event_id = emit_tool_result_for_ide(
            tool_use_id, "File not found", failed=True, error_message="File not found"
        )

        assert event_id is not None

        # Verify TOOL_RESULT event shows failure
        events = get_events(limit=10, event_type="TOOL_RESULT")
        assert len(events) > 0
        assert events[0]["payload"]["failed"] is True
        assert events[0]["payload"]["error_message"] == "File not found"

    def test_get_ide_tool_executor(self):
        """Test get_ide_tool_executor returns executor instance."""
        executor = get_ide_tool_executor()
        assert executor is not None
        assert isinstance(executor, IDEToolExecutor)
