"""Tests for session_analyzer module."""

import json
from pathlib import Path

import pytest

from divineos.analysis.session_analyzer import (
    CORRECTION_PATTERNS,
    DECISION_PATTERNS,
    ENCOURAGEMENT_PATTERNS,
    FRUSTRATION_PATTERNS,
    PREFERENCE_PATTERNS,
    _detect_signals,
    _extract_timestamps,
    _extract_user_text,
    load_records,
    _summarize_tool_input,
    analyze_session,
)
from divineos.analysis.session_discovery import (
    aggregate_analyses,
    find_sessions,
)

# --- Fixtures ---


def _make_user_record(text: str, timestamp: str = "2025-01-01T00:00:00Z") -> dict:
    """Create a minimal user record."""
    return {
        "type": "user",
        "timestamp": timestamp,
        "message": {"content": [{"type": "text", "text": text}]},
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


# --- Pattern detection tests ---


class TestPatternDetection:
    def test_correction_detected(self):
        signal = _detect_signals(
            "no that's wrong, try again", CORRECTION_PATTERNS, "correction", "ts"
        )
        assert signal is not None
        assert signal.signal_type == "correction"
        assert len(signal.patterns_matched) > 0

    def test_correction_you_missed(self):
        signal = _detect_signals(
            "you missed the main point", CORRECTION_PATTERNS, "correction", "ts"
        )
        assert signal is not None

    def test_correction_why_did_you(self):
        signal = _detect_signals(
            "why did you delete those files?", CORRECTION_PATTERNS, "correction", "ts"
        )
        assert signal is not None

    def test_no_false_positive_on_normal_text(self):
        signal = _detect_signals("sounds good lets do it", CORRECTION_PATTERNS, "correction", "ts")
        assert signal is None

    def test_encouragement_detected(self):
        signal = _detect_signals(
            "perfect that's amazing work!",
            ENCOURAGEMENT_PATTERNS,
            "encouragement",
            "ts",
        )
        assert signal is not None
        assert signal.signal_type == "encouragement"

    def test_encouragement_proud(self):
        signal = _detect_signals(
            "im very proud of you", ENCOURAGEMENT_PATTERNS, "encouragement", "ts"
        )
        assert signal is not None

    def test_decision_detected(self):
        signal = _detect_signals("yes lets use option A", DECISION_PATTERNS, "decision", "ts")
        assert signal is not None

    def test_decision_ill_go_with(self):
        signal = _detect_signals("ill go with your plan", DECISION_PATTERNS, "decision", "ts")
        assert signal is not None

    def test_frustration_detected(self):
        signal = _detect_signals(
            "did you not see what i said? lol",
            FRUSTRATION_PATTERNS,
            "frustration",
            "ts",
        )
        assert signal is not None

    def test_frustration_sigh(self):
        signal = _detect_signals("le sigh...", FRUSTRATION_PATTERNS, "frustration", "ts")
        assert signal is not None

    def test_preference_i_prefer(self):
        signal = _detect_signals(
            "i prefer plain english explanations", PREFERENCE_PATTERNS, "preference", "ts"
        )
        assert signal is not None
        assert signal.signal_type == "preference"

    def test_preference_break_it_down(self):
        signal = _detect_signals(
            "break it down like im dumb please", PREFERENCE_PATTERNS, "preference", "ts"
        )
        assert signal is not None

    def test_preference_no_jargon(self):
        signal = _detect_signals(
            "don't use jargon with me", PREFERENCE_PATTERNS, "preference", "ts"
        )
        assert signal is not None

    def test_preference_always(self):
        signal = _detect_signals(
            "always test before committing", PREFERENCE_PATTERNS, "preference", "ts"
        )
        assert signal is not None

    def test_preference_keep_it(self):
        signal = _detect_signals(
            "keep it simple and clean", PREFERENCE_PATTERNS, "preference", "ts"
        )
        assert signal is not None


# --- User text extraction tests ---


class TestExtractUserText:
    def test_simple_text_block(self):
        record = _make_user_record("hello world")
        assert _extract_user_text(record) == "hello world"

    def test_strips_system_reminder(self):
        record = {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "my question <system-reminder>hidden stuff</system-reminder>",
                    }
                ]
            },
        }
        assert _extract_user_text(record) == "my question"

    def test_empty_content(self):
        record = {"type": "user", "message": {"content": ""}}
        assert _extract_user_text(record) == ""

    def test_string_content(self):
        record = {"type": "user", "message": {"content": "direct string"}}
        assert _extract_user_text(record) == "direct string"

    def test_multiple_text_blocks(self):
        record = {
            "type": "user",
            "message": {
                "content": [
                    {"type": "text", "text": "part one"},
                    {"type": "text", "text": "part two"},
                ]
            },
        }
        assert "part one" in _extract_user_text(record)
        assert "part two" in _extract_user_text(record)


# --- Tool input summary tests ---


class TestSummarizeToolInput:
    def test_read_tool(self):
        result = _summarize_tool_input("Read", {"file_path": "/foo/bar.py"})
        assert "bar.py" in result

    def test_bash_tool(self):
        result = _summarize_tool_input("Bash", {"command": "pytest tests/"})
        assert "pytest" in result

    def test_glob_tool(self):
        result = _summarize_tool_input("Glob", {"pattern": "**/*.py"})
        assert "*.py" in result

    def test_agent_tool(self):
        result = _summarize_tool_input("Agent", {"description": "explore codebase"})
        assert "explore" in result

    def test_unknown_tool(self):
        result = _summarize_tool_input("SomeTool", {"key": "value"})
        assert result == "value"

    def test_empty_input(self):
        result = _summarize_tool_input("SomeTool", {})
        assert result == ""


# --- Timestamp extraction tests ---


class TestExtractTimestamps:
    def test_iso_timestamp(self):
        records = [{"timestamp": "2025-01-01T12:00:00Z"}]
        ts = _extract_timestamps(records)
        assert len(ts) == 1

    def test_epoch_timestamp(self):
        records = [{"timestamp": 1704067200}]
        ts = _extract_timestamps(records)
        assert len(ts) == 1

    def test_epoch_ms_timestamp(self):
        records = [{"timestamp": 1704067200000}]
        ts = _extract_timestamps(records)
        assert len(ts) == 1

    def test_no_timestamp(self):
        records = [{"type": "user"}]
        ts = _extract_timestamps(records)
        assert len(ts) == 0

    def test_bad_timestamp(self):
        records = [{"timestamp": "not-a-date"}]
        ts = _extract_timestamps(records)
        assert len(ts) == 0


# --- Full session analysis tests ---


class TestAnalyzeSession:
    def test_nonexistent_file(self, tmp_path):
        analysis = analyze_session(tmp_path / "nope.jsonl")
        assert analysis.total_records == 0

    def test_empty_session(self, tmp_path):
        session_file = _write_session(tmp_path, [])
        analysis = analyze_session(session_file)
        assert analysis.total_records == 0
        assert analysis.user_messages == 0

    def test_user_message_counted(self, tmp_path):
        records = [_make_user_record("hello")]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        assert analysis.user_messages == 1

    def test_correction_extracted(self, tmp_path):
        records = [_make_user_record("no that's wrong, you missed the point")]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        assert len(analysis.corrections) >= 1

    def test_encouragement_extracted(self, tmp_path):
        records = [_make_user_record("perfect that is amazing work!")]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        assert len(analysis.encouragements) >= 1

    def test_tool_call_tracked(self, tmp_path):
        records = [_make_assistant_record(tools=[{"name": "Bash", "input": {"command": "ls"}}])]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        assert analysis.tool_calls_total == 1
        assert analysis.tool_usage.get("Bash") == 1

    def test_multiple_tools_tracked(self, tmp_path):
        records = [
            _make_assistant_record(
                tools=[
                    {"name": "Read", "input": {"file_path": "/foo.py"}},
                    {"name": "Edit", "input": {"file_path": "/foo.py"}},
                ]
            ),
            _make_assistant_record(tools=[{"name": "Read", "input": {"file_path": "/bar.py"}}]),
        ]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        assert analysis.tool_calls_total == 3
        assert analysis.tool_usage["Read"] == 2
        assert analysis.tool_usage["Edit"] == 1

    def test_model_tracked(self, tmp_path):
        records = [_make_assistant_record(text="hello", model="claude-opus-4-6")]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        assert "claude-opus-4-6" in analysis.models_used

    def test_synthetic_model_excluded(self, tmp_path):
        records = [_make_assistant_record(text="hello", model="<synthetic>")]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        assert "<synthetic>" not in analysis.models_used

    def test_preference_extracted(self, tmp_path):
        records = [_make_user_record("i prefer plain english, no jargon please")]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        assert len(analysis.preferences) >= 1

    def test_context_overflow_detected(self, tmp_path):
        records = [
            _make_user_record(
                "This session is being continued from a previous conversation that ran out of context."
            )
        ]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        assert len(analysis.context_overflows) == 1
        # Overflow messages should NOT be classified as corrections/encouragements
        assert len(analysis.corrections) == 0

    def test_timeline_extracted(self, tmp_path):
        records = [
            _make_user_record("first", timestamp="2025-01-01T10:00:00Z"),
            _make_user_record("last", timestamp="2025-01-01T12:00:00Z"),
        ]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        assert analysis.start_time is not None
        assert analysis.end_time is not None
        assert analysis.duration_seconds == pytest.approx(7200.0, abs=1)

    def test_summary_output(self, tmp_path):
        records = [
            _make_user_record("perfect this is great"),
            _make_user_record("no that's wrong"),
            _make_assistant_record(tools=[{"name": "Bash", "input": {"command": "ls"}}]),
        ]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        summary = analysis.summary()
        assert "Session Analysis" in summary
        assert "Corrections" in summary
        assert "Encouragements" in summary

    def test_to_dict(self, tmp_path):
        records = [_make_user_record("hello")]
        session_file = _write_session(tmp_path, records)
        analysis = analyze_session(session_file)
        d = analysis.to_dict()
        assert d["user_messages"] == 1
        assert "session_id" in d


# --- Find sessions tests ---


class TestFindSessions:
    def test_finds_jsonl_files(self, tmp_path):
        (tmp_path / "session1.jsonl").write_text("{}\n")
        (tmp_path / "session2.jsonl").write_text("{}\n")
        sessions = find_sessions(tmp_path)
        assert len(sessions) == 2

    def test_excludes_subagents(self, tmp_path):
        (tmp_path / "main.jsonl").write_text("{}\n")
        sub_dir = tmp_path / "subagents"
        sub_dir.mkdir()
        (sub_dir / "agent.jsonl").write_text("{}\n")
        sessions = find_sessions(tmp_path)
        assert len(sessions) == 1
        assert "subagents" not in sessions[0].parts

    def test_empty_dir(self, tmp_path):
        sessions = find_sessions(tmp_path)
        assert sessions == []

    def test_nonexistent_dir(self, tmp_path):
        sessions = find_sessions(tmp_path / "nope")
        assert sessions == []


# --- Aggregate tests ---


class TestAggregate:
    def test_empty_list(self):
        result = aggregate_analyses([])
        assert result == {"sessions": 0}

    def test_aggregates_counts(self, tmp_path):
        records1 = [
            _make_user_record("perfect"),
            _make_user_record("no wrong"),
        ]
        records2 = [_make_user_record("amazing work")]

        f1 = _write_session(tmp_path, records1)
        f2 = tmp_path / "session2.jsonl"
        with open(f2, "w") as f:
            for r in records2:
                f.write(json.dumps(r) + "\n")

        a1 = analyze_session(f1)
        a2 = analyze_session(f2)
        agg = aggregate_analyses([a1, a2])

        assert agg["sessions"] == 2
        assert agg["total_user_messages"] == 3


# --- Load records tests ---


class TestLoadRecords:
    def test_valid_jsonl(self, tmp_path):
        f = tmp_path / "test.jsonl"
        f.write_text('{"a": 1}\n{"b": 2}\n')
        records = load_records(f)
        assert len(records) == 2

    def test_skips_bad_lines(self, tmp_path):
        f = tmp_path / "test.jsonl"
        f.write_text('{"a": 1}\nnot json\n{"b": 2}\n')
        records = load_records(f)
        assert len(records) == 2

    def test_skips_empty_lines(self, tmp_path):
        f = tmp_path / "test.jsonl"
        f.write_text('{"a": 1}\n\n{"b": 2}\n')
        records = load_records(f)
        assert len(records) == 2
