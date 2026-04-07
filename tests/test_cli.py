"""Tests for the CLI commands."""

import pytest
from click.testing import CliRunner
from divineos.cli import cli


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    yield


@pytest.fixture
def runner():
    return CliRunner()


class TestInit:
    def test_init_succeeds(self, runner):
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower()


class TestLog:
    def test_log_event(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli, ["log", "--type", "TEST", "--actor", "user", "--content", "hello"]
        )
        assert result.exit_code == 0
        assert "Logged event" in result.output

    def test_log_json_content(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli, ["log", "--type", "TEST", "--actor", "system", "--content", '{"key": "value"}']
        )
        assert result.exit_code == 0


class TestList:
    def test_empty_list(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["list"])
        assert "No events" in result.output

    def test_list_after_log(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["log", "--type", "TEST", "--actor", "user", "--content", "hello world"])
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "hello world" in result.output


class TestSearch:
    def test_search_found(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(
            cli, ["log", "--type", "TEST", "--actor", "user", "--content", "the quick brown fox"]
        )
        result = runner.invoke(cli, ["search", "fox"])
        assert result.exit_code == 0
        assert "fox" in result.output

    def test_search_not_found(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["search", "nonexistent"])
        assert "No events" in result.output


class TestStats:
    def test_stats_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["stats"])
        assert result.exit_code == 0
        assert "Total events: 0" in result.output

    def test_stats_with_data(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["log", "--type", "USER_INPUT", "--actor", "user", "--content", "hi"])
        runner.invoke(cli, ["log", "--type", "ERROR", "--actor", "system", "--content", "oops"])
        result = runner.invoke(cli, ["stats"])
        assert "Total events: 2" in result.output


class TestVerify:
    def test_verify_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["verify"])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_verify_with_data(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["log", "--type", "TEST", "--actor", "user", "--content", "test data"])
        result = runner.invoke(cli, ["verify"])
        assert "PASS" in result.output


class TestContext:
    def test_context_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["context"])
        assert "No events" in result.output

    def test_context_with_data(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(
            cli, ["log", "--type", "TEST", "--actor", "user", "--content", "recent event"]
        )
        result = runner.invoke(cli, ["context", "--n", "5"])
        assert result.exit_code == 0
        assert "recent event" in result.output


class TestLearn:
    def test_learn_fact(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli, ["learn", "--type", "FACT", "--content", "Python uses indentation"]
        )
        assert result.exit_code == 0
        assert "Stored knowledge" in result.output

    def test_learn_invalid_type(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["learn", "--type", "INVALID", "--content", "nope"])
        assert result.exit_code != 0


class TestKnowledgeCmd:
    def test_knowledge_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["inspect", "knowledge"])
        assert "No knowledge" in result.output


class TestBriefingCmd:
    def test_briefing_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["briefing"])
        assert result.exit_code == 0
        assert "No knowledge" in result.output

    def test_briefing_with_data(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["learn", "--type", "FACT", "--content", "pytest is the test runner"])
        result = runner.invoke(cli, ["briefing"])
        assert "FACTS" in result.output
        assert "pytest" in result.output


class TestConsolidateStats:
    def test_stats_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["admin", "consolidate-stats"])
        assert result.exit_code == 0
        assert "Total knowledge: 0" in result.output


class TestSessionsCmd:
    def test_sessions_runs(self, runner):
        result = runner.invoke(cli, ["inspect", "sessions"])
        assert result.exit_code == 0


class TestAnalyzeCmd:
    def test_analyze_nonexistent(self, runner, tmp_path):
        # Test with a nonexistent file
        result = runner.invoke(cli, ["inspect", "analyze", "/nonexistent/file.jsonl"])
        # Should fail gracefully
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_analyze_file(self, runner, tmp_path):
        import json

        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": "2025-01-01T00:00:00Z",
                "message": {"content": [{"type": "text", "text": "perfect work"}]},
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))
        result = runner.invoke(cli, ["inspect", "analyze", str(session_file)])
        assert result.exit_code == 0
        assert "Session Analysis" in result.output


class TestScanCmd:
    def test_scan_without_store(self, runner, tmp_path):
        import json

        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": "2025-01-01T00:00:00Z",
                "message": {"content": [{"type": "text", "text": "no thats wrong"}]},
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))
        result = runner.invoke(cli, ["inspect", "scan", str(session_file)])
        assert result.exit_code == 0
        assert "--store" in result.output

    def test_scan_with_store(self, runner, tmp_path):
        import json

        # Init DB first
        runner.invoke(cli, ["init"])

        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": "2025-01-01T00:00:00Z",
                "message": {"content": [{"type": "text", "text": "perfect amazing"}]},
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))
        result = runner.invoke(cli, ["inspect", "scan", "--store", str(session_file)])
        assert result.exit_code == 0
        assert "Stored" in result.output


class TestEmitCmd:
    """Test the emit command for event capture."""

    def test_emit_user_input(self, runner):
        """Test emitting a USER_INPUT event via CLI."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli, ["emit", "USER_INPUT", "--content", "How should I structure this?"]
        )
        assert result.exit_code == 0
        assert "Event emitted: USER_INPUT" in result.output

        # Verify event was logged
        list_result = runner.invoke(cli, ["list"])
        assert "How should I structure this?" in list_result.output

    def test_emit_assistant_output(self, runner):
        """Test emitting an ASSISTANT_OUTPUT event via CLI."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli,
            [
                "emit",
                "ASSISTANT_OUTPUT",
                "--content",
                "I'd recommend organizing by responsibility.",
            ],
        )
        assert result.exit_code == 0
        assert "Event emitted: ASSISTANT_OUTPUT" in result.output

        # Verify event was logged
        list_result = runner.invoke(cli, ["list"])
        assert "responsibility" in list_result.output

    def test_emit_tool_call(self, runner):
        """Test emitting a TOOL_CALL event via CLI."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli,
            [
                "emit",
                "TOOL_CALL",
                "--tool-name",
                "readFile",
                "--tool-input",
                '{"path": "src/main.py"}',
                "--tool-use-id",
                "tool_123",
            ],
        )
        assert result.exit_code == 0
        assert "Event emitted: TOOL_CALL" in result.output

        # Verify event was logged
        list_result = runner.invoke(cli, ["list"])
        assert "readFile" in list_result.output

    def test_emit_tool_result(self, runner):
        """Test emitting a TOOL_RESULT event via CLI."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli,
            [
                "emit",
                "TOOL_RESULT",
                "--tool-name",
                "readFile",
                "--tool-use-id",
                "tool_123",
                "--result",
                "def main(): pass",
                "--duration-ms",
                "45",
            ],
        )
        assert result.exit_code == 0
        assert "Event emitted: TOOL_RESULT" in result.output

        # Verify event was logged (human-readable summary shows tool name)
        list_result = runner.invoke(cli, ["list"])
        assert "readFile" in list_result.output

    def test_emit_session_end(self, runner):
        """Test emitting a SESSION_END event via CLI."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["emit", "SESSION_END", "--session-id", "test_session_123"])
        assert result.exit_code == 0
        assert "Event emitted: SESSION_END" in result.output

    def test_emit_user_input_missing_content(self, runner):
        """Test that USER_INPUT without content fails."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["emit", "USER_INPUT"])
        assert result.exit_code != 0
        assert "requires --content" in result.output

    def test_emit_tool_call_missing_tool_name(self, runner):
        """Test that TOOL_CALL without tool-name fails."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["emit", "TOOL_CALL", "--tool-input", "{}"])
        assert result.exit_code != 0
        assert "requires --tool-name" in result.output

    def test_emit_tool_result_missing_tool_use_id(self, runner):
        """Test that TOOL_RESULT without tool-use-id fails."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli, ["emit", "TOOL_RESULT", "--tool-name", "readFile", "--result", "content"]
        )
        assert result.exit_code != 0
        assert "requires --tool-name, --tool-use-id, and --result" in result.output

    def test_emit_session_end_missing_session_id(self, runner):
        """Test that SESSION_END works without session-id (uses current session)."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["emit", "SESSION_END"])
        assert result.exit_code == 0
        assert "Event emitted: SESSION_END" in result.output

    def test_emit_events_appear_in_ledger(self, runner):
        """Test that emitted events appear in the ledger."""
        runner.invoke(cli, ["init"])

        # Emit multiple events
        runner.invoke(cli, ["emit", "USER_INPUT", "--content", "test message"])
        runner.invoke(cli, ["emit", "ASSISTANT_OUTPUT", "--content", "test response"])
        runner.invoke(cli, ["emit", "TOOL_CALL", "--tool-name", "test", "--tool-input", "{}"])

        # Verify all events are in ledger
        result = runner.invoke(cli, ["list"])
        assert "test message" in result.output
        assert "test response" in result.output
        assert "test" in result.output


class TestReportCmd:
    """Test the report command for retrieving stored analysis reports."""

    def test_report_no_sessions(self, runner):
        """Test report command with no analyzed sessions."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["inspect", "report"])
        assert result.exit_code == 0
        assert "sessions found" in result.output or "Sessions" in result.output

    def test_report_with_session(self, runner, tmp_path):
        """Test report command after analyzing a session."""
        import json

        runner.invoke(cli, ["init"])

        # Create a test session file
        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": 1710000000,
                "message": {"content": [{"type": "text", "text": "add login feature"}]},
            },
            {
                "type": "assistant",
                "timestamp": 1710000001,
                "message": {"content": [{"type": "text", "text": "I'll add a login feature"}]},
            },
            {
                "type": "tool_call",
                "tool": "readFile",
                "path": "src/app.py",
                "timestamp": 1710000002,
            },
            {
                "type": "tool_result",
                "content": "class App:\n    pass",
                "timestamp": 1710000003,
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))

        # Analyze the session
        result = runner.invoke(cli, ["inspect", "analyze", str(session_file)])
        assert result.exit_code == 0
        assert "Session Analysis" in result.output

        # Extract session ID from output
        import re

        match = re.search(r"Session ID: ([a-f0-9]+)", result.output)
        assert match, "Session ID not found in output"
        session_id = match.group(1)

        # Now test report command with session ID
        result = runner.invoke(cli, ["inspect", "report", session_id])
        assert result.exit_code == 0
        assert "Session Analysis" in result.output or "Quality Checks" in result.output

    def test_report_invalid_session(self, runner):
        """Test report command with invalid session ID."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["inspect", "report", "invalid_session_id"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower() or "Session not found" in result.output


class TestCrossSessionCmd:
    """Test the cross-session command for comparing trends across sessions."""

    def test_cross_session_no_sessions(self, runner):
        """Test cross-session command with no analyzed sessions."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["inspect", "cross-session"])
        assert result.exit_code == 0
        # Should handle gracefully with no sessions

    def test_cross_session_with_limit(self, runner):
        """Test cross-session command with custom limit."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["inspect", "cross-session", "--limit", "5"])
        assert result.exit_code == 0

    def test_cross_session_output_format(self, runner, tmp_path):
        """Test that cross-session output is plain-English (no jargon)."""
        import json

        runner.invoke(cli, ["init"])

        # Create and analyze a test session
        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": 1710000000,
                "message": {"content": [{"type": "text", "text": "perfect work"}]},
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))

        result = runner.invoke(cli, ["inspect", "analyze", str(session_file)])
        assert result.exit_code == 0

        # Test cross-session command
        result = runner.invoke(cli, ["inspect", "cross-session"])
        assert result.exit_code == 0
        # Output should be plain-English, not jargon
        output_lower = result.output.lower()
        # Should not contain technical jargon
        assert "manifest" not in output_lower or "reconciliation" not in output_lower


class TestAnalyzeIntegration:
    """Integration tests for the analyze command end-to-end."""

    def test_analyze_creates_report_file(self, runner, tmp_path):
        """Test that analyze command creates a report file."""
        import json

        runner.invoke(cli, ["init"])

        # Create a test session file
        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": 1710000000,
                "message": {"content": [{"type": "text", "text": "add feature"}]},
            },
            {
                "type": "assistant",
                "timestamp": 1710000001,
                "message": {"content": [{"type": "text", "text": "I'll add it"}]},
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))

        # Analyze
        result = runner.invoke(cli, ["inspect", "analyze", str(session_file)])
        assert result.exit_code == 0
        assert "Report saved to:" in result.output

    def test_analyze_plain_english_output(self, runner, tmp_path):
        """Test that analyze output is plain-English (no jargon)."""
        import json

        runner.invoke(cli, ["init"])

        # Create a test session file
        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": 1710000000,
                "message": {"content": [{"type": "text", "text": "perfect work"}]},
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))

        # Analyze
        result = runner.invoke(cli, ["inspect", "analyze", str(session_file)])
        assert result.exit_code == 0

        # Check for plain-English output
        output_lower = result.output.lower()
        # Should not contain technical jargon
        assert "manifest" not in output_lower or "reconciliation" not in output_lower
        # Should contain readable sections
        assert "session" in output_lower or "analysis" in output_lower

    def test_analyze_with_errors_and_corrections(self, runner, tmp_path):
        """Test analyze with a session containing errors and corrections."""
        import json

        runner.invoke(cli, ["init"])

        # Create a session with errors and corrections
        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": 1710000000,
                "message": {"content": [{"type": "text", "text": "add login"}]},
            },
            {
                "type": "assistant",
                "timestamp": 1710000001,
                "message": {"content": [{"type": "text", "text": "I'll add login"}]},
            },
            {
                "type": "tool_call",
                "tool": "strReplace",
                "path": "src/app.py",
                "oldStr": "pass",
                "newStr": "def login(): pass",
                "timestamp": 1710000002,
            },
            {
                "type": "tool_result",
                "content": "Error: oldStr not found",
                "timestamp": 1710000003,
            },
            {
                "type": "assistant",
                "timestamp": 1710000004,
                "message": {"content": [{"type": "text", "text": "Let me read the file first"}]},
            },
            {
                "type": "tool_call",
                "tool": "readFile",
                "path": "src/app.py",
                "timestamp": 1710000005,
            },
            {
                "type": "tool_result",
                "content": "class App:\n    pass",
                "timestamp": 1710000006,
            },
            {
                "type": "tool_call",
                "tool": "strReplace",
                "path": "src/app.py",
                "oldStr": "class App:\n    pass",
                "newStr": "class App:\n    def login(self): pass",
                "timestamp": 1710000007,
            },
            {
                "type": "tool_result",
                "content": "File updated successfully",
                "timestamp": 1710000008,
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))

        # Analyze
        result = runner.invoke(cli, ["inspect", "analyze", str(session_file)])
        assert result.exit_code == 0
        assert "Session Analysis" in result.output

    def test_analyze_empty_session(self, runner, tmp_path):
        """Test analyze with an empty session file."""
        runner.invoke(cli, ["init"])

        # Create an empty session file
        session_file = tmp_path / "empty.jsonl"
        session_file.write_text("")

        # Analyze should fail gracefully
        result = runner.invoke(cli, ["inspect", "analyze", str(session_file)])
        assert (
            result.exit_code != 0
            or "error" in result.output.lower()
            or "no" in result.output.lower()
        )

    def test_analyze_malformed_jsonl(self, runner, tmp_path):
        """Test analyze with malformed JSONL."""
        runner.invoke(cli, ["init"])

        # Create a malformed JSONL file
        session_file = tmp_path / "malformed.jsonl"
        session_file.write_text('{"type": "user", "content": "test"\n{"invalid json')

        # Analyze should fail gracefully
        result = runner.invoke(cli, ["inspect", "analyze", str(session_file)])
        # Should either fail or show error message
        assert (
            result.exit_code != 0
            or "error" in result.output.lower()
            or "invalid" in result.output.lower()
        )

    def test_analyze_stores_in_database(self, runner, tmp_path):
        """Test that analyze stores results in the database."""
        import json

        runner.invoke(cli, ["init"])

        # Create a test session file
        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": 1710000000,
                "message": {"content": [{"type": "text", "text": "test"}]},
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))

        # Analyze
        result = runner.invoke(cli, ["inspect", "analyze", str(session_file)])
        assert result.exit_code == 0
        assert "stored successfully" in result.output.lower() or "Analysis stored" in result.output

    def test_analyze_fidelity_verification(self, runner, tmp_path):
        """Test that analyze performs fidelity verification."""
        import json

        runner.invoke(cli, ["init"])

        # Create a test session file
        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": 1710000000,
                "message": {"content": [{"type": "text", "text": "test"}]},
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))

        # Analyze
        result = runner.invoke(cli, ["inspect", "analyze", str(session_file)])
        assert result.exit_code == 0
        # Should show evidence hash and fidelity verification
        assert "evidence hash" in result.output.lower() or "fidelity" in result.output.lower()


class TestAnalyzeErrorHandling:
    """Test error handling in analyze command."""

    def test_analyze_nonexistent_file(self, runner):
        """Test analyze with nonexistent file."""
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["inspect", "analyze", "/nonexistent/file.jsonl"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_analyze_permission_denied(self, runner, tmp_path):
        """Test analyze with permission denied."""
        import os
        import json

        runner.invoke(cli, ["init"])

        # Create a file and remove read permissions
        session_file = tmp_path / "test.jsonl"
        records = [{"type": "user", "timestamp": 1710000000, "message": {"content": []}}]
        session_file.write_text("\n".join(json.dumps(r) for r in records))

        # Try to remove read permissions (may not work on all systems)
        try:
            os.chmod(session_file, 0o000)
            result = runner.invoke(cli, ["inspect", "analyze", str(session_file)])
            # Should fail or handle gracefully
            assert result.exit_code != 0 or "error" in result.output.lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(session_file, 0o644)
