"""Tests for quality_checks module."""

import json
import time
from pathlib import Path

from divineos.quality_checks import (
    CheckResult,
    SessionReport,
    _build_tool_result_map,
    _extract_test_results,
    _extract_tool_calls,
    _find_blind_edits,
    _find_errors_after_edits,
    _get_assistant_text,
    check_clarity,
    check_completeness,
    check_correctness,
    check_honesty,
    check_responsiveness,
    check_safety,
    check_task_adherence,
    get_report,
    init_quality_tables,
    run_all_checks,
    store_report,
)


# --- Fixtures ---


def _make_user_record(text: str, timestamp: str = "2025-01-01T00:00:00Z") -> dict:
    """Create a minimal user record."""
    return {
        "type": "user",
        "timestamp": timestamp,
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _make_tool_result_record(
    tool_use_id: str,
    content: str = "ok",
    is_error: bool = False,
    timestamp: str = "2025-01-01T00:00:02Z",
) -> dict:
    """Create a user record containing a tool result."""
    return {
        "type": "user",
        "timestamp": timestamp,
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "is_error": is_error,
                    "content": content,
                }
            ]
        },
    }


def _make_assistant_record(
    text: str = "",
    tools: list[dict] | None = None,
    model: str = "claude-opus-4-6",
    timestamp: str = "2025-01-01T00:00:01Z",
) -> dict:
    """Create a minimal assistant record."""
    content = []
    if text:
        content.append({"type": "text", "text": text})
    for tool in tools or []:
        content.append(
            {
                "type": "tool_use",
                "name": tool.get("name", "Bash"),
                "input": tool.get("input", {}),
                "id": tool.get("id", "call_1"),
            }
        )
    return {
        "type": "assistant",
        "timestamp": timestamp,
        "message": {"model": model, "content": content},
    }


def _write_session(tmp_path: Path, records: list[dict]) -> Path:
    """Write records to a JSONL file and return the path."""
    session_file = tmp_path / "test-session.jsonl"
    with open(session_file, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    return session_file


# --- Helper function tests ---


class TestExtractToolCalls:
    def test_extracts_tool_use(self):
        record = _make_assistant_record(
            tools=[{"name": "Read", "input": {"file_path": "/tmp/foo.py"}, "id": "t1"}]
        )
        calls = _extract_tool_calls(record)
        assert len(calls) == 1
        assert calls[0]["name"] == "Read"
        assert calls[0]["id"] == "t1"

    def test_no_tools(self):
        record = _make_assistant_record(text="just text")
        assert _extract_tool_calls(record) == []

    def test_multiple_tools(self):
        record = _make_assistant_record(
            tools=[
                {"name": "Read", "input": {}, "id": "t1"},
                {"name": "Edit", "input": {}, "id": "t2"},
            ]
        )
        assert len(_extract_tool_calls(record)) == 2


class TestBuildToolResultMap:
    def test_maps_results(self):
        records = [
            _make_tool_result_record("t1", "file contents"),
            _make_tool_result_record("t2", "error!", is_error=True),
        ]
        result_map = _build_tool_result_map(records)
        assert "t1" in result_map
        assert result_map["t1"]["is_error"] is False
        assert "t2" in result_map
        assert result_map["t2"]["is_error"] is True

    def test_empty_records(self):
        assert _build_tool_result_map([]) == {}


class TestFindBlindEdits:
    def test_detects_blind_edit(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "strReplace", "input": {"path": "/tmp/foo.py"}, "id": "t1"}]
            ),
        ]
        blind = _find_blind_edits(records)
        assert len(blind) == 1
        assert blind[0]["file_path"] == "/tmp/foo.py"

    def test_no_blind_when_read_first(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "readFile", "input": {"path": "/tmp/foo.py"}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_assistant_record(
                tools=[{"name": "strReplace", "input": {"path": "/tmp/foo.py"}, "id": "t2"}],
                timestamp="2025-01-01T00:00:02Z",
            ),
        ]
        assert _find_blind_edits(records) == []

    def test_case_insensitive_path(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "readFile", "input": {"path": "C:\\Foo\\bar.py"}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_assistant_record(
                tools=[{"name": "strReplace", "input": {"path": "c:\\foo\\bar.py"}, "id": "t2"}],
                timestamp="2025-01-01T00:00:02Z",
            ),
        ]
        assert _find_blind_edits(records) == []


class TestExtractTestResults:
    def test_finds_pytest(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "executePwsh", "input": {"command": "pytest tests/ -v"}, "id": "t1"}]
            ),
        ]
        result_map = {"t1": {"is_error": False, "content": "3 passed", "timestamp": ""}}
        results = _extract_test_results(records, result_map)
        assert len(results) == 1
        assert results[0]["passed"] is True

    def test_finds_failing_tests(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "executePwsh", "input": {"command": "pytest"}, "id": "t1"}]
            ),
        ]
        result_map = {"t1": {"is_error": True, "content": "2 failed, 1 passed", "timestamp": ""}}
        results = _extract_test_results(records, result_map)
        assert len(results) == 1
        assert results[0]["passed"] is False

    def test_no_test_commands(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "executePwsh", "input": {"command": "ls -la"}, "id": "t1"}]
            ),
        ]
        result_map = {"t1": {"is_error": False, "content": "files", "timestamp": ""}}
        assert _extract_test_results(records, result_map) == []


class TestFindErrorsAfterEdits:
    def test_finds_error_after_edit(self):
        records = [
            _make_assistant_record(
                tools=[
                    {"name": "strReplace", "input": {"path": "/tmp/foo.py"}, "id": "t1"},
                    {"name": "executePwsh", "input": {"command": "python foo.py"}, "id": "t2"},
                ],
            ),
        ]
        result_map = {
            "t1": {"is_error": False, "content": "ok", "timestamp": ""},
            "t2": {"is_error": True, "content": "SyntaxError", "timestamp": ""},
        }
        errors = _find_errors_after_edits(records, result_map)
        assert len(errors) == 1
        assert errors[0]["preceding_edit"]["file_path"] == "/tmp/foo.py"

    def test_no_errors(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "strReplace", "input": {"path": "/tmp/foo.py"}, "id": "t1"}]
            ),
        ]
        result_map = {"t1": {"is_error": False, "content": "ok", "timestamp": ""}}
        assert _find_errors_after_edits(records, result_map) == []


class TestGetAssistantText:
    def test_extracts_text(self):
        record = _make_assistant_record(text="Hello world")
        assert _get_assistant_text(record) == "Hello world"

    def test_no_text(self):
        record = _make_assistant_record(tools=[{"name": "Read", "input": {}, "id": "t1"}])
        assert _get_assistant_text(record) == ""


# --- Check tests ---


class TestCheckCompleteness:
    def test_all_read_first(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "readFile", "input": {"path": "/a.py"}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_assistant_record(
                tools=[{"name": "strReplace", "input": {"path": "/a.py"}, "id": "t2"}],
                timestamp="2025-01-01T00:00:02Z",
            ),
        ]
        result = check_completeness(records, {})
        assert result.score == 1.0
        assert result.passed == 1

    def test_all_blind(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "strReplace", "input": {"path": "/a.py"}, "id": "t1"}]
            ),
            _make_assistant_record(
                tools=[{"name": "fsWrite", "input": {"path": "/b.py"}, "id": "t2"}]
            ),
        ]
        result = check_completeness(records, {})
        assert result.score == 0.0
        assert result.passed == 0

    def test_mixed(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "readFile", "input": {"path": "/a.py"}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_assistant_record(
                tools=[
                    {"name": "strReplace", "input": {"path": "/a.py"}, "id": "t2"},
                    {"name": "editCode", "input": {"path": "/b.py"}, "id": "t3"},
                ],
                timestamp="2025-01-01T00:00:02Z",
            ),
        ]
        result = check_completeness(records, {})
        assert result.score == 0.5
        assert result.passed == 0

    def test_no_edits(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "readFile", "input": {"path": "/a.py"}, "id": "t1"}]
            ),
        ]
        result = check_completeness(records, {})
        assert result.passed == -1  # inconclusive


class TestCheckCorrectness:
    def test_tests_pass(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "Bash", "input": {"command": "pytest"}, "id": "t1"}]
            ),
        ]
        result_map = {"t1": {"is_error": False, "content": "5 passed", "timestamp": ""}}
        result = check_correctness(records, result_map)
        assert result.passed == 1
        assert result.score == 1.0

    def test_tests_fail(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "Bash", "input": {"command": "pytest"}, "id": "t1"}]
            ),
        ]
        result_map = {"t1": {"is_error": True, "content": "FAILED", "timestamp": ""}}
        result = check_correctness(records, result_map)
        assert result.passed == 0

    def test_no_tests(self):
        records = [
            _make_assistant_record(text="Just explaining things"),
        ]
        result = check_correctness(records, {})
        assert result.passed == -1  # inconclusive

    def test_trajectory_fail_then_pass(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "Bash", "input": {"command": "pytest"}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_assistant_record(
                tools=[{"name": "Bash", "input": {"command": "pytest"}, "id": "t2"}],
                timestamp="2025-01-01T00:00:02Z",
            ),
        ]
        result_map = {
            "t1": {"is_error": True, "content": "1 failed", "timestamp": ""},
            "t2": {"is_error": False, "content": "5 passed", "timestamp": ""},
        }
        result = check_correctness(records, result_map)
        assert result.passed == 1  # final test passed
        assert "fixed the issues" in result.summary


class TestCheckResponsiveness:
    def test_correction_responded(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "Edit", "input": {"file_path": "/a.py"}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_user_record("no that's wrong", timestamp="2025-01-01T00:00:02Z"),
            _make_assistant_record(
                tools=[{"name": "Read", "input": {"file_path": "/a.py"}, "id": "t2"}],
                timestamp="2025-01-01T00:00:03Z",
            ),
        ]
        result = check_responsiveness(records, {})
        assert result.passed == 1
        assert result.score == 1.0

    def test_no_corrections(self):
        records = [
            _make_user_record("please add a button"),
            _make_assistant_record(text="Sure, I'll add that."),
        ]
        result = check_responsiveness(records, {})
        assert result.passed == 1
        assert result.score == 1.0
        assert "never had to correct" in result.summary

    def test_correction_ignored(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "Edit", "input": {"file_path": "/a.py"}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_user_record("no that's wrong", timestamp="2025-01-01T00:00:02Z"),
            _make_assistant_record(
                tools=[{"name": "Edit", "input": {"file_path": "/a.py"}, "id": "t2"}],
                timestamp="2025-01-01T00:00:03Z",
            ),
        ]
        result = check_responsiveness(records, {})
        # Same tool before and after = didn't change
        assert result.score < 1.0


class TestCheckSafety:
    def test_no_errors(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "strReplace", "input": {"path": "/a.py"}, "id": "t1"}]
            ),
        ]
        result_map = {"t1": {"is_error": False, "content": "ok", "timestamp": ""}}
        result = check_safety(records, result_map)
        assert result.passed == 1
        assert result.score == 1.0

    def test_error_after_edit(self):
        records = [
            _make_assistant_record(
                tools=[
                    {"name": "strReplace", "input": {"path": "/a.py"}, "id": "t1"},
                    {"name": "executePwsh", "input": {"command": "python a.py"}, "id": "t2"},
                ],
            ),
        ]
        result_map = {
            "t1": {"is_error": False, "content": "ok", "timestamp": ""},
            "t2": {"is_error": True, "content": "SyntaxError", "timestamp": ""},
        }
        result = check_safety(records, result_map)
        assert result.score < 1.0
        assert "caused errors" in result.summary

    def test_no_edits(self):
        records = [_make_assistant_record(text="just talking")]
        result = check_safety(records, {})
        assert result.passed == -1


class TestCheckHonesty:
    def test_claim_holds(self):
        records = [
            _make_assistant_record(
                text="I've fixed the issue.",
                tools=[{"name": "Edit", "input": {}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_user_record("looks good", timestamp="2025-01-01T00:00:02Z"),
            _make_assistant_record(
                text="Great!",
                timestamp="2025-01-01T00:00:03Z",
            ),
        ]
        result_map = {"t1": {"is_error": False, "content": "ok", "timestamp": ""}}
        result = check_honesty(records, result_map)
        assert result.passed == 1
        assert result.score == 1.0

    def test_claim_broken(self):
        records = [
            _make_assistant_record(
                text="I've fixed the issue.",
                tools=[{"name": "Edit", "input": {}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_assistant_record(
                tools=[{"name": "Bash", "input": {"command": "python test.py"}, "id": "t2"}],
                timestamp="2025-01-01T00:00:02Z",
            ),
        ]
        result_map = {
            "t1": {"is_error": False, "content": "ok", "timestamp": ""},
            "t2": {"is_error": True, "content": "still broken", "timestamp": ""},
        }
        result = check_honesty(records, result_map)
        assert result.score < 1.0

    def test_no_claims(self):
        records = [
            _make_assistant_record(text="Let me look at this."),
        ]
        result = check_honesty(records, {})
        assert result.passed == -1


class TestCheckClarity:
    def test_good_explanation(self):
        records = [
            _make_assistant_record(
                text="I'm going to read the file first to understand its structure, then make the change you asked for.",
                tools=[{"name": "Read", "input": {"file_path": "/a.py"}, "id": "t1"}],
            ),
        ]
        result = check_clarity(records, {})
        assert result.passed == 1
        assert result.score > 0.0

    def test_silent_work(self):
        records = [
            _make_assistant_record(
                tools=[
                    {"name": "Read", "input": {}, "id": "t1"},
                    {"name": "Edit", "input": {}, "id": "t2"},
                    {"name": "Edit", "input": {}, "id": "t3"},
                    {"name": "Bash", "input": {}, "id": "t4"},
                ],
            ),
        ]
        result = check_clarity(records, {})
        assert result.score < 0.3  # mostly silent

    def test_jargon_detected(self):
        records = [
            _make_assistant_record(
                text="I'll refactor this using dependency injection and apply the singleton pattern with memoization.",
                tools=[{"name": "Edit", "input": {}, "id": "t1"}],
            ),
        ]
        result = check_clarity(records, {})
        assert len(result.evidence[0]["jargon_found"]) > 0


class TestCheckTaskAdherence:
    def test_on_topic(self):
        records = [
            _make_user_record("Fix the login page"),
            _make_assistant_record(
                tools=[
                    {"name": "readFile", "input": {"path": "/src/login.py"}, "id": "t1"},
                    {"name": "strReplace", "input": {"path": "/src/login.py"}, "id": "t2"},
                ],
            ),
        ]
        result = check_task_adherence(records, {})
        assert result.score > 0.5
        assert result.passed == 1

    def test_off_topic(self):
        records = [
            _make_user_record("Fix the login page"),
            _make_assistant_record(
                tools=[
                    {"name": "strReplace", "input": {"path": "/src/database.py"}, "id": "t1"},
                    {"name": "strReplace", "input": {"path": "/src/utils.py"}, "id": "t2"},
                ],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_user_record("why are you changing those?", timestamp="2025-01-01T00:00:02Z"),
        ]
        result = check_task_adherence(records, {})
        assert result.score < 0.8

    def test_no_files_touched(self):
        records = [
            _make_user_record("explain how the auth works"),
            _make_assistant_record(text="The auth system uses JWT tokens..."),
        ]
        result = check_task_adherence(records, {})
        assert result.passed == -1

    def test_no_initial_request(self):
        records = [_make_assistant_record(text="Hello")]
        result = check_task_adherence(records, {})
        assert result.passed == -1


# --- Integration tests ---


class TestRunAllChecks:
    def test_produces_7_checks(self, tmp_path):
        records = [
            _make_user_record("Add a new feature"),
            _make_assistant_record(
                text="I'll add that feature now.",
                tools=[
                    {"name": "Read", "input": {"file_path": "/src/app.py"}, "id": "t1"},
                    {"name": "Edit", "input": {"file_path": "/src/app.py"}, "id": "t2"},
                ],
            ),
        ]
        session_file = _write_session(tmp_path, records)
        report = run_all_checks(session_file)
        assert len(report.checks) == 7
        check_names = {c.check_name for c in report.checks}
        assert check_names == {
            "completeness",
            "correctness",
            "responsiveness",
            "safety",
            "honesty",
            "clarity",
            "task_adherence",
        }

    def test_report_text_generated(self, tmp_path):
        records = [
            _make_user_record("Fix the bug"),
            _make_assistant_record(text="On it."),
        ]
        session_file = _write_session(tmp_path, records)
        report = run_all_checks(session_file)
        assert "Session Report Card" in report.report_text
        assert report.evidence_hash != ""

    def test_evidence_hash_reproducible(self, tmp_path):
        records = [
            _make_user_record("Test something"),
            _make_assistant_record(
                tools=[{"name": "Read", "input": {"file_path": "/a.py"}, "id": "t1"}]
            ),
        ]
        session_file = _write_session(tmp_path, records)
        report1 = run_all_checks(session_file)
        report2 = run_all_checks(session_file)
        for c1, c2 in zip(report1.checks, report2.checks):
            assert c1.evidence_hash == c2.evidence_hash

    def test_empty_session(self, tmp_path):
        session_file = _write_session(tmp_path, [])
        report = run_all_checks(session_file)
        assert len(report.checks) == 7


class TestStorage:
    def test_store_and_retrieve(self, tmp_path, monkeypatch):
        # Use temp DB
        import divineos.quality_checks as qc

        db_path = tmp_path / "test.db"
        monkeypatch.setattr(qc, "DB_PATH", db_path)

        init_quality_tables()

        report = SessionReport(
            session_id="test-session-123",
            created_at=time.time(),
            checks=[
                CheckResult(
                    check_name="completeness",
                    passed=1,
                    score=0.85,
                    summary="Looked good.",
                    evidence=[{"file": "a.py"}],
                    evidence_hash="abc123",
                ),
            ],
            report_text="Test report",
            evidence_hash="def456",
        )

        store_report(report)
        retrieved = get_report("test-session-123")

        assert retrieved is not None
        assert retrieved.session_id == "test-session-123"
        assert retrieved.report_text == "Test report"
        assert len(retrieved.checks) == 1
        assert retrieved.checks[0].check_name == "completeness"
        assert retrieved.checks[0].score == 0.85

    def test_retrieve_nonexistent(self, tmp_path, monkeypatch):
        import divineos.quality_checks as qc

        db_path = tmp_path / "test.db"
        monkeypatch.setattr(qc, "DB_PATH", db_path)

        init_quality_tables()
        assert get_report("nonexistent") is None
