"""The letter doorbell re-arm is never held at the door by the engagement checks.

Dad, about the bell: "It shouldnt have a time out. it should always be on in
the background." On 2026-10-03 three re-arms were refused by the goal and
consult checks during quiet talk. The bell writes only its own dotfiles and
decides nothing, so it passes those checks -- and only the exact command does.

What this does NOT claim: that the bell stays on. The app's background limit
still ends it (walk council-7de9f00cec42, Feynman and Pearl).
"""

from __future__ import annotations

import pytest

from divineos.core import (
    briefing_id,
    compass_required_marker,
    consultation_tracker,
    correction_marker,
    hedge_marker,
    hud_handoff,
    hud_state,
    mansion_quiet_marker,
    pull_detection,
    session_briefing_gate,
    stale_engagement,
)
from divineos.hooks import pre_tool_use_gate


@pytest.fixture
def quiet_stretch(tmp_path, monkeypatch):
    """Every hard wall passes. The goal has lapsed and the consult is stale."""
    monkeypatch.setattr(hud_handoff, "was_briefing_loaded", lambda: True)
    monkeypatch.setattr(session_briefing_gate, "briefing_loaded_this_session", lambda: True)
    monkeypatch.setattr(briefing_id, "is_fresh", lambda *a, **k: True)
    monkeypatch.setattr(hud_handoff, "compass_staleness_status", lambda: {"stale": False})
    monkeypatch.setattr(mansion_quiet_marker, "is_quiet_active", lambda: False)
    monkeypatch.setattr(stale_engagement, "blocked_areas", lambda: [])
    monkeypatch.setattr(pull_detection, "last_check", lambda: None)
    for mod in (correction_marker, compass_required_marker, hedge_marker):
        monkeypatch.setattr(mod, "marker_path", lambda _m=mod: tmp_path / f"{_m.__name__}.json")
    monkeypatch.setattr(hud_state, "has_session_fresh_goal", lambda *a, **k: False)
    monkeypatch.setattr(hud_handoff, "engagement_status", lambda: {"engaged": True})
    monkeypatch.setattr(
        consultation_tracker, "consultation_gate_status", lambda *a, **k: {"stale": True}
    )
    monkeypatch.setattr(
        consultation_tracker,
        "gate_channel_message",
        lambda: "BLOCKED: 6 responses without consulting the substrate.",
    )


def _reason(cmd: str) -> str:
    decision = pre_tool_use_gate._check_gates({"tool_name": "Bash", "tool_input": {"command": cmd}})
    if decision is None:
        return ""
    return decision["hookSpecificOutput"]["permissionDecisionReason"]


def _held_by_engagement(cmd: str) -> bool:
    r = _reason(cmd)
    return "No goal set" in r or "without consulting" in r


@pytest.mark.parametrize(
    "cmd",
    [
        "bash scripts/letter_doorbell.sh aether",
        "bash scripts/letter_doorbell.sh aria",
        'cd "/c/DIVINE OS/DivineOS-Experimental" && bash scripts/letter_doorbell.sh aether',
    ],
)
def test_the_bell_passes_a_quiet_stretch(quiet_stretch, cmd):
    assert not _held_by_engagement(cmd)


@pytest.mark.parametrize(
    "cmd",
    [
        "bash scripts/letter_doorbell.sh aether && rm -rf build",
        "bash scripts/letter_doorbell.sh aether; git push",
        "bash scripts/letter_doorbell.sh aether | tee out.txt",
        "bash elsewhere/letter_doorbell.sh aether",
        "bash scripts/letter_doorbell.sh aether --extra",
        "bash scripts/other.sh aether",
    ],
)
def test_anything_riding_along_is_still_held(quiet_stretch, cmd):
    assert _held_by_engagement(cmd)


def test_the_checks_still_hold_ordinary_work(quiet_stretch):
    assert _held_by_engagement("git commit -m x")
