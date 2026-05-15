"""Regression-pin tests for OS-native SessionStart orchestrator.

Andrew 2026-05-14 night: load-briefing.sh was a 197-line bash hook
with session-state reset, briefing rendering, payload shaping, and
diagnostic logging all embedded. session_start is the OS-native
replacement; the hook is now a thin doorman.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from divineos.core.session_start import (
    log_session_start,
    render_session_start_context,
    reset_session_state,
)


def test_reset_session_state_creates_checkpoint_file(tmp_path: Path) -> None:
    """reset_session_state writes a fresh checkpoint_state.json with
    zero counters. Pins the per-session state shape."""
    checkpoint = tmp_path / "checkpoint_state.json"
    with (
        patch("divineos.core.session_start._DIVINEOS_DIR", tmp_path),
        patch("divineos.core.session_start._CHECKPOINT_STATE", checkpoint),
    ):
        reset_session_state()
        assert checkpoint.exists()
        state = json.loads(checkpoint.read_text(encoding="utf-8"))
        assert state["edits"] == 0
        assert state["tool_calls"] == 0
        assert state["checkpoints_run"] == 0


def test_reset_session_state_clears_auto_session_end_marker(tmp_path: Path) -> None:
    """The auto_session_end_emitted marker gets cleared so the next
    session can run its extract once without the prior marker blocking."""
    marker = tmp_path / "auto_session_end_emitted"
    marker.write_text("stale", encoding="utf-8")
    with (
        patch("divineos.core.session_start._DIVINEOS_DIR", tmp_path),
        patch("divineos.core.session_start._AUTO_SESSION_END_MARKER", marker),
    ):
        reset_session_state()
        assert not marker.exists()


def test_render_returns_full_when_under_threshold(tmp_path: Path) -> None:
    """When briefing+hud fits under the size threshold, the full
    wrapped context is returned with outcome 'injected_full'."""

    def _fake_render():
        return ("BRIEFING_CONTENT", "HUD_CONTENT")

    with patch("divineos.core.session_start.render_briefing_and_hud", _fake_render):
        context, diag = render_session_start_context(size_threshold=10000)
        assert "DIVINEOS SESSION START" in context
        assert "BRIEFING_CONTENT" in context
        assert "HUD_CONTENT" in context
        assert diag["outcome"] == "injected_full"


def test_render_returns_nudge_when_over_threshold(tmp_path: Path) -> None:
    """When briefing+hud exceeds the size threshold, the nudge form
    is returned with outcome 'injected_nudge'. The nudge tells the
    agent to run divineos briefing manually."""

    def _fake_render():
        return ("X" * 20000, "Y" * 5000)

    with patch("divineos.core.session_start.render_briefing_and_hud", _fake_render):
        context, diag = render_session_start_context(size_threshold=15000)
        assert "too large to auto-inject" in context
        assert "divineos briefing" in context
        assert diag["outcome"] == "injected_nudge"


def test_render_returns_empty_when_briefing_fails(tmp_path: Path) -> None:
    """Empty briefing → outcome 'empty_briefing' and empty context.
    The hook should not inject anything in this case."""

    def _fake_render():
        return ("", "")

    with patch("divineos.core.session_start.render_briefing_and_hud", _fake_render):
        context, diag = render_session_start_context()
        assert context == ""
        assert diag["outcome"] == "empty_briefing"


def test_log_session_start_writes_jsonl(tmp_path: Path) -> None:
    """Diagnostics are appended as JSON lines for after-the-fact
    debugging of whether the hook actually fired and in what shape."""
    log_file = tmp_path / "session_start_log.jsonl"
    with patch("divineos.core.session_start._SESSION_START_LOG", log_file):
        log_session_start(
            {
                "outcome": "injected_full",
                "payload_bytes": 1000,
                "briefing_bytes": 800,
                "hud_bytes": 200,
            }
        )
        assert log_file.exists()
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["outcome"] == "injected_full"
        assert entry["payload_bytes"] == 1000
