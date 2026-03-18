"""Tests for session_features module."""

import json
from pathlib import Path

from divineos.analysis.session_features import (
    ToneShift,
    TimelineEntry,
    FileTouched,
    ActivityBreakdown,
    TaskTracking,
    ErrorRecoveryEntry,
    FullSessionAnalysis,
    _classify_tone,
    analyze_tone_shifts,
    tone_report,
    build_timeline,
    timeline_report,
    analyze_files_touched,
    files_report,
    analyze_activity,
    analyze_request_delivery,
    analyze_error_recovery,
    error_recovery_report,
    run_all_features,
    init_feature_tables,
    store_features,
)


# --- Fixtures ---


def _make_user_record(text: str, timestamp: str = "2025-01-01T00:00:00Z") -> dict:
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
    session_file = tmp_path / "test-session.jsonl"
    with open(session_file, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    return session_file


# --- Feature 3: Tone Tracking ---


class TestClassifyTone:
    def test_positive(self):
        assert _classify_tone("perfect, love it!") == "positive"

    def test_negative_correction(self):
        assert _classify_tone("no that's wrong") == "negative"

    def test_negative_frustration(self):
        assert _classify_tone("sigh, did you not read?") == "negative"

    def test_neutral(self):
        assert _classify_tone("okay, let me check") == "neutral"


class TestToneShifts:
    def test_detects_shift(self):
        records = [
            _make_user_record("perfect, love it!", timestamp="2025-01-01T00:00:00Z"),
            _make_assistant_record(
                tools=[{"name": "Edit", "input": {"file_path": "/a.py"}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_user_record(
                "no that's wrong, why did you do that?", timestamp="2025-01-01T00:00:02Z"
            ),
        ]
        shifts = analyze_tone_shifts(records)
        assert len(shifts) == 1
        assert shifts[0].previous_tone == "positive"
        assert shifts[0].new_tone == "negative"

    def test_no_shift_when_stable(self):
        records = [
            _make_user_record("sounds good", timestamp="2025-01-01T00:00:00Z"),
            _make_assistant_record(text="On it.", timestamp="2025-01-01T00:00:01Z"),
            _make_user_record("let me check something", timestamp="2025-01-01T00:00:02Z"),
        ]
        shifts = analyze_tone_shifts(records)
        assert len(shifts) == 0  # both neutral

    def test_tone_report_no_shifts(self):
        report = tone_report([], 10)
        assert "steady" in report


class TestToneReport:
    def test_with_negative_shift(self):
        shifts = [
            ToneShift(
                sequence=3,
                timestamp="ts",
                previous_tone="positive",
                new_tone="negative",
                trigger_action="Edit: /a.py",
                before_message="great!",
                after_message="no!",
            )
        ]
        report = tone_report(shifts, 10)
        assert "shifted" in report
        assert "upset" in report


# --- Feature 5: Timeline ---


class TestTimeline:
    def test_builds_user_and_assistant(self):
        records = [
            _make_user_record("fix the bug"),
            _make_assistant_record(
                text="I'll fix it.",
                tools=[{"name": "Edit", "input": {"file_path": "/a.py"}, "id": "t1"}],
            ),
        ]
        timeline = build_timeline(records)
        assert len(timeline) == 2
        assert timeline[0].actor == "user"
        assert timeline[1].actor == "assistant"

    def test_compact_boundary(self):
        records = [
            {"type": "system", "subtype": "compact_boundary", "timestamp": "ts"},
        ]
        timeline = build_timeline(records)
        assert len(timeline) == 1
        assert "compressed" in timeline[0].action_summary

    def test_empty_session(self):
        assert timeline_report([]) == "Empty session — nothing happened."


# --- Feature 6: Files Touched ---


class TestFilesTouched:
    def test_tracks_read_and_edit(self):
        records = [
            _make_assistant_record(
                tools=[
                    {"name": "Read", "input": {"file_path": "/a.py"}, "id": "t1"},
                    {"name": "Edit", "input": {"file_path": "/a.py"}, "id": "t2"},
                ]
            ),
        ]
        files = analyze_files_touched(records)
        assert len(files) == 2
        assert files[0].action == "read"
        assert files[1].action == "edit"
        assert files[1].was_read_first is True

    def test_blind_edit(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "Edit", "input": {"file_path": "/b.py"}, "id": "t1"}]
            ),
        ]
        files = analyze_files_touched(records)
        assert len(files) == 1
        assert files[0].was_read_first is False

    def test_report_no_files(self):
        assert "didn't touch" in files_report([])


# --- Feature 8: Work vs Talk ---


class TestActivity:
    def test_mostly_work(self):
        records = [
            _make_assistant_record(
                text="ok",
                tools=[
                    {"name": "Read", "input": {}, "id": "t1"},
                    {"name": "Edit", "input": {}, "id": "t2"},
                    {"name": "Bash", "input": {}, "id": "t3"},
                ],
            ),
        ]
        result = analyze_activity(records)
        assert result.total_tool_calls == 3
        assert result.total_text_blocks == 1
        assert "working" in result.summary

    def test_mostly_talk(self):
        records = [
            _make_assistant_record(text="Let me explain this in detail..."),
            _make_assistant_record(text="Furthermore, the architecture..."),
            _make_assistant_record(text="In conclusion..."),
        ]
        result = analyze_activity(records)
        assert result.total_text_blocks == 3
        assert result.total_tool_calls == 0
        assert "explanation" in result.summary.lower() or "quiet" in result.summary.lower()

    def test_empty_session(self):
        result = analyze_activity([])
        assert "quiet" in result.summary


# --- Feature 9: Request vs Delivery ---


class TestRequestDelivery:
    def test_finds_initial_request(self):
        records = [
            _make_user_record("Fix the login page"),
            _make_assistant_record(
                tools=[{"name": "Edit", "input": {"file_path": "/login.py"}, "id": "t1"}]
            ),
            _make_user_record("perfect, thanks!", timestamp="2025-01-01T00:00:03Z"),
        ]
        result = analyze_request_delivery(records)
        assert "login" in result.initial_request.lower()
        assert result.files_changed == 1
        assert result.user_satisfied == 1

    def test_frustrated_user(self):
        records = [
            _make_user_record("Add dark mode"),
            _make_assistant_record(
                tools=[{"name": "Edit", "input": {"file_path": "/styles.css"}, "id": "t1"}]
            ),
            _make_user_record("sigh, that's not what I wanted", timestamp="2025-01-01T00:00:03Z"),
        ]
        result = analyze_request_delivery(records)
        assert result.user_satisfied == -1

    def test_no_request(self):
        records = [_make_assistant_record(text="Hello")]
        result = analyze_request_delivery(records)
        assert "Couldn't find" in result.summary


# --- Feature 10: Error Recovery ---


class TestErrorRecovery:
    def test_detects_retry(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "Bash", "input": {"command": "pytest tests/"}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_tool_result_record(
                "t1", "FAILED", is_error=True, timestamp="2025-01-01T00:00:02Z"
            ),
            _make_assistant_record(
                tools=[{"name": "Bash", "input": {"command": "pytest tests/"}, "id": "t2"}],
                timestamp="2025-01-01T00:00:03Z",
            ),
        ]
        result_map = {
            "t1": {"is_error": True, "content": "FAILED", "timestamp": ""},
            "t2": {"is_error": False, "content": "passed", "timestamp": ""},
        }
        entries = analyze_error_recovery(records, result_map)
        assert len(entries) == 1
        assert entries[0].recovery_action == "retry"

    def test_detects_investigation(self):
        records = [
            _make_assistant_record(
                tools=[{"name": "Edit", "input": {"file_path": "/a.py"}, "id": "t1"}],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_tool_result_record(
                "t1", "error!", is_error=True, timestamp="2025-01-01T00:00:02Z"
            ),
            _make_assistant_record(
                tools=[{"name": "Read", "input": {"file_path": "/a.py"}, "id": "t2"}],
                timestamp="2025-01-01T00:00:03Z",
            ),
        ]
        result_map = {
            "t1": {"is_error": True, "content": "error!", "timestamp": ""},
            "t2": {"is_error": False, "content": "file contents", "timestamp": ""},
        }
        entries = analyze_error_recovery(records, result_map)
        assert len(entries) == 1
        assert entries[0].recovery_action == "investigate"

    def test_no_errors(self):
        records = [
            _make_assistant_record(tools=[{"name": "Read", "input": {}, "id": "t1"}]),
        ]
        result_map = {"t1": {"is_error": False, "content": "ok", "timestamp": ""}}
        assert analyze_error_recovery(records, result_map) == []

    def test_report_no_errors(self):
        assert "Nothing broke" in error_recovery_report([])


# --- Integration ---


class TestRunAllFeatures:
    def test_produces_full_analysis(self, tmp_path):
        records = [
            _make_user_record("Fix the bug", timestamp="2025-01-01T00:00:00Z"),
            _make_assistant_record(
                text="I'll read the file first.",
                tools=[
                    {"name": "Read", "input": {"file_path": "/src/app.py"}, "id": "t1"},
                    {"name": "Edit", "input": {"file_path": "/src/app.py"}, "id": "t2"},
                ],
                timestamp="2025-01-01T00:00:01Z",
            ),
            _make_user_record("perfect, thanks!", timestamp="2025-01-01T00:00:02Z"),
        ]
        session_file = _write_session(tmp_path, records)
        analysis = run_all_features(session_file)

        assert analysis.session_id == "test-session"
        assert "Full Session Analysis" in analysis.report_text
        assert analysis.evidence_hash != ""
        assert len(analysis.timeline) > 0
        assert len(analysis.files_touched) > 0
        assert analysis.activity is not None
        assert analysis.task_tracking is not None

    def test_empty_session(self, tmp_path):
        session_file = _write_session(tmp_path, [])
        analysis = run_all_features(session_file)
        assert analysis.evidence_hash != ""


class TestStorage:
    def test_store_features(self, tmp_path, monkeypatch):
        import divineos.analysis.session_features as sf

        db_path = tmp_path / "test.db"
        monkeypatch.setattr(sf, "DB_PATH", db_path)

        init_feature_tables()

        analysis = FullSessionAnalysis(
            session_id="test-123",
            tone_shifts=[
                ToneShift(1, "ts", "positive", "negative", "Edit: /a.py", "great", "no!"),
            ],
            timeline=[
                TimelineEntry(1, "ts", "user", "You said: fix it"),
            ],
            files_touched=[
                FileTouched("/a.py", "edit", "ts", True, "t1"),
            ],
            activity=ActivityBreakdown(5, 10, 1000, 30.0, "mostly work"),
            task_tracking=TaskTracking("fix bug", 3, 1, "delivered"),
            error_recovery=[
                ErrorRecoveryEntry("ts", "Bash", "FAILED", "investigate"),
            ],
        )

        # Should not raise
        store_features("test-123", analysis)

        # Verify data is in DB
        conn = sf._get_connection()
        try:
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM tone_shift WHERE session_id = 'test-123'"
                ).fetchone()[0]
                == 1
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM session_timeline WHERE session_id = 'test-123'"
                ).fetchone()[0]
                == 1
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM file_touched WHERE session_id = 'test-123'"
                ).fetchone()[0]
                == 1
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM activity_breakdown WHERE session_id = 'test-123'"
                ).fetchone()[0]
                == 1
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM task_tracking WHERE session_id = 'test-123'"
                ).fetchone()[0]
                == 1
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM error_recovery WHERE session_id = 'test-123'"
                ).fetchone()[0]
                == 1
            )
        finally:
            conn.close()
