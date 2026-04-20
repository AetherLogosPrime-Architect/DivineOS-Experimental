"""Tests for the write-count consolidation trigger (PR #2 commit 2).

Locked invariants:

1. Every ledger event emission increments writes_since_consolidation EXCEPT
   consolidation events themselves.
2. Non-consolidation event types all count the same (1 per event).
3. Successful `divineos extract` resets the counter to 0.
4. reset_state() (session-start) initializes the counter to 0.
5. CONSOLIDATION_WRITE_THRESHOLD default is 40.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from divineos.core.session_checkpoint import (
    CONSOLIDATION_WRITE_THRESHOLD,
    _counter_path,
    _load_state,
    increment_write_count,
    reset_state,
    reset_write_count,
)


@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    reset_state()
    marker = Path(os.path.expanduser("~")) / ".divineos" / "auto_session_end_emitted"
    if marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass
    yield
    reset_state()
    if marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass


class TestThresholdConstant:
    def test_threshold_is_pinned_at_40(self):
        assert CONSOLIDATION_WRITE_THRESHOLD == 40


class TestIncrementGuard:
    def test_non_consolidation_event_increments(self):
        count = increment_write_count("USER_INPUT")
        assert count == 1

    def test_multiple_events_accumulate(self):
        increment_write_count("USER_INPUT")
        increment_write_count("TOOL_CALL")
        count = increment_write_count("DECISION_RECORDED")
        assert count == 3

    def test_session_end_does_NOT_increment(self):
        increment_write_count("USER_INPUT")
        count = increment_write_count("SESSION_END")
        assert count == 1

    def test_consolidation_checkpoint_does_NOT_increment(self):
        increment_write_count("USER_INPUT")
        count = increment_write_count("CONSOLIDATION_CHECKPOINT")
        assert count == 1

    def test_counter_persists_to_disk(self):
        increment_write_count("USER_INPUT")
        increment_write_count("TOOL_CALL")
        import json

        raw = json.loads(_counter_path().read_text(encoding="utf-8"))
        assert raw["writes_since_consolidation"] == 2


class TestResetBehavior:
    def test_reset_write_count_zeros_counter(self):
        increment_write_count("USER_INPUT")
        increment_write_count("TOOL_CALL")
        reset_write_count()
        state = _load_state()
        assert state["writes_since_consolidation"] == 0

    def test_reset_write_count_preserves_other_fields(self):
        increment_write_count("USER_INPUT")
        state = _load_state()
        state["edits"] = 5
        state["tool_calls"] = 10
        from divineos.core.session_checkpoint import _save_state

        _save_state(state)

        reset_write_count()
        after = _load_state()
        assert after["writes_since_consolidation"] == 0
        assert after["edits"] == 5
        assert after["tool_calls"] == 10

    def test_reset_state_initializes_counter(self):
        reset_state()
        state = _load_state()
        assert state["writes_since_consolidation"] == 0


class TestLogEventIntegration:
    """log_event calls increment_write_count. Integration point."""

    def test_log_event_increments_counter(self):
        from divineos.core.ledger import init_db, log_event

        init_db()
        reset_write_count()
        log_event("USER_INPUT", "user", {"content": "test message"})
        state = _load_state()
        assert state["writes_since_consolidation"] == 1

    def test_log_event_consolidation_does_NOT_increment(self):
        from divineos.core.ledger import init_db, log_event

        init_db()
        reset_write_count()
        log_event(
            "CONSOLIDATION_CHECKPOINT",
            "system",
            {
                "session_id": "test-session-xyz",
                "message_count": 0,
                "tool_call_count": 0,
                "tool_result_count": 0,
                "duration_seconds": 0.0,
                "timestamp": "2026-04-20T00:00:00Z",
            },
        )
        state = _load_state()
        assert state["writes_since_consolidation"] == 0


class TestExtractResetsCounter:
    def test_successful_extract_resets_counter(self):
        from click.testing import CliRunner

        from divineos.cli import cli

        increment_write_count("USER_INPUT")
        increment_write_count("TOOL_CALL")
        increment_write_count("DECISION_RECORDED")
        assert _load_state()["writes_since_consolidation"] == 3

        runner = CliRunner()
        runner.invoke(cli, ["init"])
        with patch("divineos.cli.event_commands._run_session_end_pipeline"):
            result = runner.invoke(cli, ["extract"])
        assert result.exit_code == 0
        assert _load_state()["writes_since_consolidation"] == 0
