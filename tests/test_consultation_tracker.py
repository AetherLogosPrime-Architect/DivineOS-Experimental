"""Tests for consultation_tracker — substrate-query-to-response ratio.

Aletheia hidden-issues audit 2026-05-20 (Finding B): heavily wired (10
call sites) substrate-shaping module with zero tests. The ratio thresholds
that drive the briefing surface and the session-key isolation are the
load-bearing logic.
"""

from __future__ import annotations

import pytest

from divineos.core import consultation_tracker


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """Redirect the module-level state file (bound at import) to tmp, and
    fix the session id so the bucket is deterministic."""
    monkeypatch.setattr(
        consultation_tracker, "_STATE_FILE", tmp_path / "consultation_state.json"
    )
    monkeypatch.setenv("CLAUDE_SESSION_ID", "sess-A")
    monkeypatch.delenv("DIVINEOS_SESSION_ID", raising=False)
    return tmp_path


class TestRecordAndStats:
    def test_query_and_response_counted(self, isolated_state):
        consultation_tracker.record_query("ask")
        consultation_tracker.record_query("recall")
        consultation_tracker.record_response()
        s = consultation_tracker.session_stats()
        assert s["queries"] == 2
        assert s["responses"] == 1
        assert s["ratio"] == 2.0
        assert s["tools_used"] == ["ask", "recall"]

    def test_ratio_zero_when_no_responses(self, isolated_state):
        consultation_tracker.record_query("ask")
        assert consultation_tracker.session_stats()["ratio"] == 0.0

    def test_tools_used_deduped_and_sorted(self, isolated_state):
        for tool in ("recall", "ask", "ask", "compass"):
            consultation_tracker.record_query(tool)
        assert consultation_tracker.session_stats()["tools_used"] == ["ask", "compass", "recall"]


class TestSessionIsolation:
    def test_distinct_sessions_separate_buckets(self, isolated_state, monkeypatch):
        consultation_tracker.record_query("ask")
        consultation_tracker.record_response()
        # Switch session — stats should reset to the new bucket.
        monkeypatch.setenv("CLAUDE_SESSION_ID", "sess-B")
        s = consultation_tracker.session_stats()
        assert s["queries"] == 0
        assert s["responses"] == 0


class TestBriefingThresholds:
    def _drive(self, queries: int, responses: int):
        for _ in range(queries):
            consultation_tracker.record_query("ask")
        for _ in range(responses):
            consultation_tracker.record_response()

    def test_empty_when_too_few_responses(self, isolated_state):
        # r < 3 → too early to judge.
        self._drive(queries=0, responses=2)
        assert consultation_tracker.briefing_block() == ""

    def test_healthy_when_ratio_at_least_half(self, isolated_state):
        # 3 queries / 4 responses = 0.75 >= 0.5 → HEALTHY.
        self._drive(queries=3, responses=4)
        assert "HEALTHY" in consultation_tracker.briefing_block()

    def test_degraded_band(self, isolated_state):
        # 1 query / 4 responses = 0.25 → DEGRADED (0.2 <= ratio < 0.5).
        self._drive(queries=1, responses=4)
        block = consultation_tracker.briefing_block()
        assert "DEGRADED" in block

    def test_severe_band(self, isolated_state):
        # 0 queries / 4 responses = 0.0 → SEVERE (ratio < 0.2).
        self._drive(queries=0, responses=4)
        assert "SEVERE" in consultation_tracker.briefing_block()
