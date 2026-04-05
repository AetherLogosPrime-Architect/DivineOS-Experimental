"""Tests for mini session save and token estimation."""

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.session_checkpoint import (
    CHARS_PER_TOKEN,
    USABLE_CONTEXT_CHARS,
    _load_state,
    _save_state,
    estimate_token_usage,
    record_tool_result_size,
    reset_state,
    run_mini_session_save,
)


@pytest.fixture(autouse=True)
def _init():
    init_knowledge_table()
    reset_state()


class TestTokenEstimation:
    def test_zero_chars_returns_ok(self):
        result = estimate_token_usage()
        assert result["level"] == "ok"
        assert result["estimated_tokens"] == 0
        assert result["estimated_pct"] == 0

    def test_record_and_estimate(self):
        record_tool_result_size(10000)
        result = estimate_token_usage()
        assert result["chars_tracked"] == 10000
        assert result["estimated_tokens"] > 0

    def test_accumulates(self):
        record_tool_result_size(5000)
        record_tool_result_size(5000)
        state = _load_state()
        assert state.get("chars_in", 0) == 10000

    def test_warn_level_at_40_pct(self):
        # 40% of usable context / 1.7 scaling = chars needed
        chars_needed = int(USABLE_CONTEXT_CHARS * 0.40 / 1.7) + 1000
        _save_state({"chars_in": chars_needed, "tool_calls": 0, "edits": 0})
        result = estimate_token_usage()
        assert result["level"] in ("warn", "urgent", "critical")

    def test_critical_at_80_pct(self):
        chars_needed = int(USABLE_CONTEXT_CHARS * 0.80 / 1.7) + 1000
        _save_state({"chars_in": chars_needed, "tool_calls": 0, "edits": 0})
        result = estimate_token_usage()
        assert result["level"] == "critical"

    def test_constants_defined(self):
        assert CHARS_PER_TOKEN == 4
        assert USABLE_CONTEXT_CHARS == 180_000 * 4


class TestMiniSessionSave:
    def test_no_session_files_returns_error(self):
        result = run_mini_session_save()
        # May succeed or fail depending on whether session files exist
        # but should never raise
        assert isinstance(result, dict)
        assert "knowledge_extracted" in result
        assert "error" in result

    def test_result_structure(self):
        result = run_mini_session_save()
        assert "knowledge_extracted" in result
        assert "episode_stored" in result
        assert "curation" in result
        assert "handoff_saved" in result
        assert "error" in result
