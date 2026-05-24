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
    monkeypatch.setattr(consultation_tracker, "_STATE_FILE", tmp_path / "consultation_state.json")
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


class TestConsultationGate:
    """Gate+channel: block substrate-modifying tools after N responses with
    no substantive consult; clear only on a real consult (Andrew 2026-05-23)."""

    def _responses(self, n: int):
        for _ in range(n):
            consultation_tracker.record_response()

    def test_not_stale_below_threshold(self, isolated_state):
        self._responses(3)  # threshold is 4
        assert consultation_tracker.consultation_gate_status()["stale"] is False

    def test_stale_at_threshold(self, isolated_state):
        self._responses(4)
        st = consultation_tracker.consultation_gate_status()
        assert st["stale"] is True
        assert st["responses_since"] == 4

    def test_substantive_consult_clears_gate(self, isolated_state):
        self._responses(6)
        assert consultation_tracker.consultation_gate_status()["stale"] is True
        consultation_tracker.record_query("ask")
        st = consultation_tracker.consultation_gate_status()
        assert st["stale"] is False
        assert st["responses_since"] == 0

    def test_cheap_read_does_not_clear_gate(self, isolated_state):
        # hud/context are not substantive — they must NOT reset the counter,
        # or the gate is gameable via a status peek.
        self._responses(5)
        consultation_tracker.record_query("hud")
        consultation_tracker.record_query("context")
        assert consultation_tracker.consultation_gate_status()["stale"] is True

    def test_counter_climbs_again_after_consult(self, isolated_state):
        # A single consult can't cover an unbounded later run.
        self._responses(5)
        consultation_tracker.record_query("ask")
        assert consultation_tracker.consultation_gate_status()["stale"] is False
        self._responses(4)
        assert consultation_tracker.consultation_gate_status()["stale"] is True

    def test_channel_message_offers_the_path(self, isolated_state):
        self._responses(5)
        msg = consultation_tracker.gate_channel_message()
        assert "BLOCKED" in msg
        assert "divineos ask" in msg
        # The channel names the way, not just the no.
        assert "Here is the way" in msg


class TestGateClearCommandsAreBypassed:
    """Every substantive-consult command the gate names as its remedy must be
    in the PreToolUse bypass set, or the gate blocks its own remedy."""

    def test_clearing_commands_bypass_all_gates(self):
        from divineos.hooks.pre_tool_use_gate import _BYPASS_DIVINEOS_SUBCOMMANDS

        for cmd in ("ask", "recall", "corrections", "directives", "active", "compass"):
            assert cmd in _BYPASS_DIVINEOS_SUBCOMMANDS, f"{cmd} must bypass"


class TestSessionKeyMarkerFallback:
    """The bucket-split fix (2026-05-24, claim ba6dc25a): when the session
    env var is unset, _session_key() must fall back to the canonical
    current_session.txt marker BEFORE the daily bucket — so the CLI (which
    sets the env var from this marker) and a hook (which has no env var)
    resolve the SAME key. Without this, writes and reads land in different
    buckets and the gate fires false SEVERE forever."""

    def _no_env(self, monkeypatch):
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("DIVINEOS_SESSION_ID", raising=False)

    def test_marker_used_when_env_unset(self, tmp_path, monkeypatch):
        self._no_env(monkeypatch)
        monkeypatch.setattr(consultation_tracker, "divineos_home", lambda: tmp_path)
        (tmp_path / "current_session.txt").write_text("sess-marker", encoding="utf-8")
        assert consultation_tracker._session_key() == "sess-marker"

    def test_env_takes_precedence_over_marker(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DIVINEOS_SESSION_ID", raising=False)
        monkeypatch.setenv("CLAUDE_SESSION_ID", "sess-env")
        monkeypatch.setattr(consultation_tracker, "divineos_home", lambda: tmp_path)
        (tmp_path / "current_session.txt").write_text("sess-marker", encoding="utf-8")
        assert consultation_tracker._session_key() == "sess-env"

    def test_daily_bucket_only_when_no_env_and_no_marker(self, tmp_path, monkeypatch):
        self._no_env(monkeypatch)
        monkeypatch.setattr(consultation_tracker, "divineos_home", lambda: tmp_path)
        # No marker written.
        assert consultation_tracker._session_key().startswith("daily-")

    def test_blank_marker_falls_through_to_daily(self, tmp_path, monkeypatch):
        self._no_env(monkeypatch)
        monkeypatch.setattr(consultation_tracker, "divineos_home", lambda: tmp_path)
        (tmp_path / "current_session.txt").write_text("   \n", encoding="utf-8")
        assert consultation_tracker._session_key().startswith("daily-")
