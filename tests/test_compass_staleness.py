"""Tests for compass-staleness structural enforcement gate.

Falsifiability:
  - Fresh session (no code actions yet) reports stale=False.
  - Below-threshold code action count reports stale=False.
  - At/above-threshold reports stale=True with correct actions_since.
  - reset_compass_actions_counter zeroes the counter.
  - Gate integration: stale compass triggers pre_tool_use_gate deny.
  - No engagement marker present -> stale=False (fail-open).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from divineos.core import hud_handoff, session_briefing_gate


def _install_engagement_marker(tmp_path: Path, counter: int) -> Path:
    """Install an engagement marker with a specific compass_actions_since."""
    hud_dir = tmp_path / "hud"
    hud_dir.mkdir()
    marker = hud_dir / ".session_engaged"
    marker.write_text(
        json.dumps(
            {
                "engaged_at": 1.0,
                "code_actions_since": counter,
                "compass_actions_since": counter,
                "deep_actions_since": counter,
            }
        ),
        encoding="utf-8",
    )
    return hud_dir


class TestStalenessStatus:
    def test_no_marker_returns_fresh(self, tmp_path) -> None:
        with patch.object(hud_handoff, "_ensure_hud_dir", return_value=tmp_path):
            status = hud_handoff.compass_staleness_status()
        assert status["stale"] is False
        assert status["actions_since"] == 0

    def test_below_threshold_not_stale(self, tmp_path) -> None:
        hud_dir = _install_engagement_marker(tmp_path, counter=5)
        with patch.object(hud_handoff, "_ensure_hud_dir", return_value=hud_dir):
            status = hud_handoff.compass_staleness_status()
        assert status["stale"] is False
        assert status["actions_since"] == 5

    def test_above_threshold_is_stale(self, tmp_path) -> None:
        hud_dir = _install_engagement_marker(tmp_path, counter=50)
        with patch.object(hud_handoff, "_ensure_hud_dir", return_value=hud_dir):
            status = hud_handoff.compass_staleness_status()
        assert status["stale"] is True
        assert status["actions_since"] == 50
        assert status["threshold"] > 0


class TestCounterReset:
    def test_reset_zeroes_counter(self, tmp_path) -> None:
        hud_dir = _install_engagement_marker(tmp_path, counter=50)
        with patch.object(hud_handoff, "_ensure_hud_dir", return_value=hud_dir):
            hud_handoff.reset_compass_actions_counter()
            status = hud_handoff.compass_staleness_status()
        assert status["actions_since"] == 0
        assert status["stale"] is False

    def test_reset_no_marker_is_safe(self, tmp_path) -> None:
        hud_dir = tmp_path / "hud"
        hud_dir.mkdir()
        with patch.object(hud_handoff, "_ensure_hud_dir", return_value=hud_dir):
            hud_handoff.reset_compass_actions_counter()  # no raise

    def test_reset_records_last_obs_timestamp(self, tmp_path) -> None:
        hud_dir = _install_engagement_marker(tmp_path, counter=10)
        with patch.object(hud_handoff, "_ensure_hud_dir", return_value=hud_dir):
            hud_handoff.reset_compass_actions_counter()
            marker = json.loads((hud_dir / ".session_engaged").read_text(encoding="utf-8"))
        assert "last_compass_obs_at" in marker
        assert marker["last_compass_obs_at"] > 0


class TestGateIntegration:
    def test_gate_denies_when_stale(self, tmp_path) -> None:
        """Stale compass triggers pre_tool_use_gate deny."""
        from divineos.hooks import pre_tool_use_gate

        hud_dir = _install_engagement_marker(tmp_path, counter=100)
        with (
            patch.object(hud_handoff, "was_briefing_loaded", return_value=True),
            patch.object(session_briefing_gate, "briefing_loaded_this_session", return_value=True),
            patch.object(hud_handoff, "_ensure_hud_dir", return_value=hud_dir),
        ):
            decision = pre_tool_use_gate._check_gates()
        assert decision is not None
        assert "compass" in str(decision).lower()

    def test_gate_passes_when_fresh(self, tmp_path) -> None:
        """Fresh compass counter should not trigger the compass gate
        (though other gates may still fire — we only verify compass is
        not the reason)."""
        from divineos.hooks import pre_tool_use_gate

        hud_dir = _install_engagement_marker(tmp_path, counter=2)
        with (
            patch.object(hud_handoff, "was_briefing_loaded", return_value=True),
            patch.object(session_briefing_gate, "briefing_loaded_this_session", return_value=True),
            patch.object(hud_handoff, "_ensure_hud_dir", return_value=hud_dir),
        ):
            decision = pre_tool_use_gate._check_gates()
        if decision is not None:
            assert (
                "compass" not in str(decision).lower() or "observation" not in str(decision).lower()
            )
