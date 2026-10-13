"""The letter doorbell re-arm is never held at the door by the engagement checks.

Dad, about the bell: "It shouldnt have a time out. it should always be on in
the background." On 2026-10-03 three re-arms were refused by the goal and
consult checks during quiet talk. The bell writes only its own dotfiles and
decides nothing, so it passes those checks -- and only the exact command does.

Tightened after Aletheia's audit the same day (walk council-0d96371ec724):
the seat word must be THIS seat, because arming another seat's bell silently
replaces theirs; and a leading cd may only land on this repository's root,
because the script path is relative.

What this does NOT claim: that the bell stays on. The app's background limit
still ends it (walk council-7de9f00cec42, Feynman and Pearl).
"""

from __future__ import annotations

from pathlib import Path

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
    sibling_audit_rounds,
    stale_engagement,
)
from divineos.core.auto_commit import find_repo_root
from divineos.hooks import pre_tool_use_gate

ROOT = find_repo_root(Path(pre_tool_use_gate.__file__))


@pytest.fixture
def quiet_stretch(tmp_path, monkeypatch):
    """Every hard wall passes. The goal has lapsed and the consult is stale.
    This seat is aether."""
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
    monkeypatch.setattr(sibling_audit_rounds, "this_seat", lambda: "aether")
    return monkeypatch


def _reason(cmd: str) -> str:
    decision = pre_tool_use_gate._check_gates({"tool_name": "Bash", "tool_input": {"command": cmd}})
    if decision is None:
        return ""
    return decision["hookSpecificOutput"]["permissionDecisionReason"]


def _held_by_engagement(cmd: str) -> bool:
    r = _reason(cmd)
    return "No goal set" in r or "without consulting" in r


def _git_bash(p: Path) -> str:
    s = p.as_posix()
    return f"/{s[0].lower()}{s[2:]}" if len(s) > 1 and s[1] == ":" else s


@pytest.mark.parametrize(
    "cmd",
    [
        "bash scripts/letter_doorbell.sh aether",
        "bash ./scripts/letter_doorbell.sh aether",
        f'cd "{ROOT}" && bash scripts/letter_doorbell.sh aether',
        f'cd "{_git_bash(ROOT)}" && bash scripts/letter_doorbell.sh aether',
    ],
)
def test_my_own_bell_passes_a_quiet_stretch(quiet_stretch, cmd):
    assert not _held_by_engagement(cmd)


@pytest.mark.parametrize(
    "cmd",
    [
        # Aletheia's first hole: another seat's word silently replaces their bell.
        "bash scripts/letter_doorbell.sh aria",
        "bash scripts/letter_doorbell.sh nobody",
        # Aletheia's second hole: a cd elsewhere runs another checkout's copy.
        "cd /tmp/evil && bash scripts/letter_doorbell.sh aether",
        "cd .. && bash scripts/letter_doorbell.sh aether",
        f'cd "{ROOT / "scripts"}" && bash scripts/letter_doorbell.sh aether',
        # Anything riding along.
        "bash scripts/letter_doorbell.sh aether && rm -rf build",
        "bash scripts/letter_doorbell.sh aether; git push",
        "bash scripts/letter_doorbell.sh aether | tee out.txt",
        "bash elsewhere/letter_doorbell.sh aether",
        "bash scripts/letter_doorbell.sh aether --extra",
        "bash scripts/other.sh aether",
    ],
)
def test_anything_else_is_still_held(quiet_stretch, cmd):
    assert _held_by_engagement(cmd)


def test_an_unknown_seat_holds_even_the_right_word(quiet_stretch):
    quiet_stretch.setattr(sibling_audit_rounds, "this_seat", lambda: None)
    assert _held_by_engagement("bash scripts/letter_doorbell.sh aether")


def test_the_other_seat_passes_its_own_bell(quiet_stretch):
    quiet_stretch.setattr(sibling_audit_rounds, "this_seat", lambda: "aria")
    assert not _held_by_engagement("bash scripts/letter_doorbell.sh aria")
    assert _held_by_engagement("bash scripts/letter_doorbell.sh aether")


def test_the_checks_still_hold_ordinary_work(quiet_stretch):
    assert _held_by_engagement("git commit -m x")
