"""Tests for session-scoped analysis via timestamp filtering."""

import json
import time

from divineos.analysis.session_analyzer import (
    _filter_records_since,
    _slim_record,
    analyze_session,
    load_records,
)
from divineos.core.session_checkpoint import get_session_start_time, reset_state


class TestFilterRecordsSince:
    def test_keeps_records_after_timestamp(self):
        records = [
            {
                "type": "user",
                "timestamp": "2026-04-01T00:00:00+00:00",
                "message": {"content": "old"},
            },
            {
                "type": "user",
                "timestamp": "2026-04-03T00:00:00+00:00",
                "message": {"content": "new"},
            },
        ]
        # Filter to after April 2
        from datetime import datetime, timezone

        cutoff = datetime(2026, 4, 2, tzinfo=timezone.utc).timestamp()
        filtered = _filter_records_since(records, cutoff)
        assert len(filtered) == 1
        assert filtered[0]["message"]["content"] == "new"

    def test_keeps_records_without_timestamps(self):
        records = [
            {"type": "user", "message": {"content": "no timestamp"}},
            {
                "type": "user",
                "timestamp": "2026-04-03T00:00:00+00:00",
                "message": {"content": "has ts"},
            },
        ]
        from datetime import datetime, timezone

        cutoff = datetime(2026, 4, 2, tzinfo=timezone.utc).timestamp()
        filtered = _filter_records_since(records, cutoff)
        assert len(filtered) == 2  # both kept

    def test_handles_epoch_timestamps(self):
        now = time.time()
        old = now - 7200  # 2 hours ago
        records = [
            {"type": "user", "timestamp": old, "message": {"content": "old"}},
            {"type": "user", "timestamp": now, "message": {"content": "new"}},
        ]
        cutoff = now - 3600  # 1 hour ago
        filtered = _filter_records_since(records, cutoff)
        assert len(filtered) == 1
        assert filtered[0]["message"]["content"] == "new"

    def test_handles_millisecond_epoch(self):
        now = time.time()
        records = [
            {"type": "user", "timestamp": now * 1000, "message": {"content": "ms epoch"}},
        ]
        cutoff = now - 10
        filtered = _filter_records_since(records, cutoff)
        assert len(filtered) == 1

    def test_empty_records(self):
        assert _filter_records_since([], 1000.0) == []

    def test_all_filtered_out(self):
        records = [
            {"type": "user", "timestamp": 1000.0, "message": {"content": "ancient"}},
        ]
        filtered = _filter_records_since(records, 9999999999.0)
        assert len(filtered) == 0


class TestAnalyzeSessionWithTimestamp:
    def test_filters_old_corrections(self, tmp_path):
        """Corrections from before the session boundary are not counted."""
        now = time.time()
        old = now - 7200  # 2 hours ago

        jsonl = tmp_path / "test_session.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": old,
                "message": {"role": "user", "content": "no that is wrong"},
            },
            {
                "type": "user",
                "timestamp": old + 10,
                "message": {"role": "user", "content": "you missed the point"},
            },
            {
                "type": "user",
                "timestamp": now,
                "message": {"role": "user", "content": "wonderful this is perfect"},
            },
        ]
        jsonl.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

        # Full analysis: should see corrections
        full = analyze_session(jsonl)
        assert len(full.corrections) >= 1

        # Scoped analysis: only the recent encouragement
        scoped = analyze_session(jsonl, since_timestamp=now - 60)
        assert len(scoped.corrections) == 0
        assert len(scoped.encouragements) >= 1

    def test_none_timestamp_analyzes_everything(self, tmp_path):
        """Passing None gives full-transcript analysis (backward compatible)."""
        now = time.time()
        jsonl = tmp_path / "test_session.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": now - 7200,
                "message": {"role": "user", "content": "no wrong"},
            },
            {"type": "user", "timestamp": now, "message": {"role": "user", "content": "perfect"}},
        ]
        jsonl.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

        analysis = analyze_session(jsonl, since_timestamp=None)
        assert analysis.total_records == 2


class TestLoadRecordsStreaming:
    """Test that load_records with since_timestamp skips old records during parse."""

    def test_stream_filter_skips_old_records(self, tmp_path):
        now = time.time()
        old = now - 7200
        records = [
            {"type": "user", "timestamp": old, "message": {"content": "old msg"}},
            {"type": "user", "timestamp": old + 10, "message": {"content": "also old"}},
            {"type": "user", "timestamp": now, "message": {"content": "current"}},
        ]
        path = tmp_path / "session.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

        loaded = load_records(path, since_timestamp=now - 60)
        assert len(loaded) == 1
        assert loaded[0]["message"]["content"] == "current"

    def test_stream_filter_none_loads_all(self, tmp_path):
        records = [
            {"type": "user", "timestamp": 1000.0, "message": {"content": "a"}},
            {"type": "user", "timestamp": 2000.0, "message": {"content": "b"}},
        ]
        path = tmp_path / "session.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

        loaded = load_records(path, since_timestamp=None)
        assert len(loaded) == 2

    def test_stream_filter_keeps_no_timestamp_records(self, tmp_path):
        now = time.time()
        records = [
            {"type": "system", "message": {"content": "no ts"}},
            {"type": "user", "timestamp": now, "message": {"content": "has ts"}},
        ]
        path = tmp_path / "session.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

        loaded = load_records(path, since_timestamp=now - 60)
        assert len(loaded) == 2  # both kept

    def test_slim_truncates_tool_use_inputs(self):
        record = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll read the file"},
                    {
                        "type": "tool_use",
                        "id": "abc",
                        "name": "Read",
                        "input": {"file_path": "/some/path.py", "extra_data": "x" * 10000},
                    },
                ],
            },
        }
        slimmed = _slim_record(record)
        blocks = slimmed["message"]["content"]
        assert blocks[0]["text"] == "I'll read the file"  # text preserved
        assert blocks[1]["name"] == "Read"  # tool name preserved
        assert "_summary" in blocks[1]["input"]  # input replaced with summary
        assert "extra_data" not in blocks[1]["input"]  # bloat removed

    def test_slim_truncates_user_tool_results(self):
        big_content = "x" * 5000
        record = {
            "type": "user",
            "message": {
                "content": [
                    {"type": "text", "text": "here's my question"},
                    {"type": "tool_result", "content": big_content},
                ],
            },
        }
        slimmed = _slim_record(record)
        blocks = slimmed["message"]["content"]
        assert blocks[0]["text"] == "here's my question"  # text preserved
        assert len(blocks[1]["content"]) < 600  # truncated

    def test_slim_preserves_small_content(self):
        record = {
            "type": "user",
            "message": {
                "content": [
                    {"type": "tool_result", "content": "short result"},
                ],
            },
        }
        slimmed = _slim_record(record)
        assert slimmed["message"]["content"][0]["content"] == "short result"

    def test_slim_with_stream_filter(self, tmp_path):
        now = time.time()
        records = [
            {
                "type": "assistant",
                "timestamp": now,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "t1",
                            "name": "Bash",
                            "input": {"command": "ls", "output": "x" * 10000},
                        },
                    ],
                },
            },
        ]
        path = tmp_path / "session.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

        loaded = load_records(path, since_timestamp=now - 60, slim=True)
        assert len(loaded) == 1
        block = loaded[0]["message"]["content"][0]
        assert block["name"] == "Bash"
        assert "_summary" in block["input"]


class TestGetSessionStartTime:
    def test_returns_from_checkpoint_state(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        (tmp_path / ".divineos").mkdir()
        reset_state()
        start = get_session_start_time()
        assert start is not None
        assert abs(start - time.time()) < 5  # within 5 seconds of now

    def test_returns_none_when_no_state(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        # No checkpoint file, no ledger events
        start = get_session_start_time()
        # Should return the session_start from _load_state default (time.time())
        assert start is not None
