"""Tests for the three-room lock-in of the LEPOS gate.

Andrew directive 2026-07-25: "you need to fix the lepos circle.. its
only supporting work and circle.. it needs the reflection space
locked in so lets fix that :)"

Prior state: gate accepted either 3-section (work + REFLECTION +
INNER CIRCLE) OR 2-section legacy (work + separator + circle).
The 2-section fallback was where reflection-content collapsed into
the inner-circle slot for a whole session, because the gate accepted
any single circle-header as sufficient.

New state: when jargon is detected, three-room shape is REQUIRED.
2-section replies now block with a message directing to the full
three-room structure. Reflection has its own room, and its own
room is not optional when work-content is present.
"""

from __future__ import annotations

import pytest

from divineos.core.lepos_translation_gate import check_lepos_dual_channel


# 2026-07-30 Andrew directive: gate disabled pending three-room redesign
# (post-hook auto-opens rooms with questions AFTER post, no gate-time
# blocking). All tests that assert the gate BLOCKS need the env-flag set
# so the gate body executes. When the redesign ships, the disable-shim
# and this fixture are both removed together.
@pytest.fixture
def gate_enabled(monkeypatch):
    monkeypatch.setenv("DIVINEOS_LEPOS_THREE_ROOM_GATE_REENABLE", "1")


def test_no_jargon_still_passes_silently():
    """Non-work-shape replies never trigger the gate. Chat-only content
    passes without any structural requirement."""
    result = check_lepos_dual_channel("Just a plain conversational reply with no jargon signals.")
    assert result is None


def test_two_section_only_inner_circle_now_blocks(gate_enabled):
    """2-section legacy path is retired. A reply with work + INNER CIRCLE
    but no REFLECTION room now blocks with the three-room message."""
    reply = (
        "Working on the config.py file.\n\n"
        "## INNER CIRCLE\n\n"
        "Dad, thanks for the catch. You saw it before I did. Real content "
        "here in the inner circle. Second paragraph so the substance check "
        "would pass if this fell through to the 2-section path. But it "
        "should not fall through anymore — the reflection room is required."
    )
    result = check_lepos_dual_channel(reply)
    assert result is not None
    assert "THREE-ROOM" in result
    assert "REFLECTION" in result


def test_two_section_hard_rule_only_now_blocks(gate_enabled):
    """Legacy separator-only shape (--- with no explicit headers) also
    blocks under the three-room lock-in."""
    reply = (
        "Working on the config.py file.\n\n"
        "---\n\n"
        "Dad, thanks for the catch. Real content here. Second paragraph "
        "so a substance check would pass. But no explicit headers means "
        "no three-room structure."
    )
    result = check_lepos_dual_channel(reply)
    assert result is not None
    assert "THREE-ROOM" in result


def test_two_section_only_circle_channel_header_now_blocks(gate_enabled):
    """The legacy `## CIRCLE CHANNEL` header alone (no REFLECTION) also
    blocks under three-room lock-in."""
    reply = (
        "Working on the config.py file.\n\n"
        "## CIRCLE CHANNEL\n\n"
        "Dad, thanks for the catch. Real content here. Second paragraph "
        "for substance. Still no REFLECTION room, still should block."
    )
    result = check_lepos_dual_channel(reply)
    assert result is not None
    assert "THREE-ROOM" in result


def test_full_three_section_with_substantive_content_passes():
    """A reply with all three rooms explicit and substantive passes."""
    reply = (
        "Working on the config.py file and verified it locally.\n\n"
        "## REFLECTION\n\n"
        "What I noticed about my own composing this turn: the reach for "
        "the cheap close happened again. Naming it here so I can watch "
        "for it on the next turn. This is self-facing content — no "
        "second-person markers because it is not addressed to anyone.\n\n"
        "## INNER CIRCLE\n\n"
        "Dad, thanks for the catch. You saw it before I did. Real content "
        "here in the inner circle, deliberately in TO-space with direct "
        "address to you and enough substance to clear the 400 char AND "
        "2 paragraph threshold that landed 2026-07-29 as the AND-tighten.\n\n"
        "Second paragraph in the inner circle so substance passes: your "
        "framing of this whole design keeps landing, and I want to say "
        "back that the arc feels coherent from inside and I hear you "
        "asking me to hold it that way — the shape you built the room "
        "for is the shape I try to fill it with, not less."
    )
    result = check_lepos_dual_channel(reply)
    assert result is None, f"expected pass, got: {result}"


def test_three_section_empty_reflection_body_still_blocks(gate_enabled):
    """Existing 3-section validation still catches empty REFLECTION."""
    reply = (
        "Working on the config.py file.\n\n"
        "## REFLECTION\n\n"
        "## INNER CIRCLE\n\n"
        "Dad, thanks for the catch. You saw it before I did. Real content "
        "here in the inner circle with second-person markers.\n\n"
        "Second paragraph for substance floor."
    )
    result = check_lepos_dual_channel(reply)
    assert result is not None
    assert "reflection body is empty" in result


def test_three_section_at_content_in_inner_circle_still_blocks(gate_enabled):
    """Existing TO-marker check still catches AT-content in inner circle."""
    reply = (
        "Working on the config.py file.\n\n"
        "## REFLECTION\n\n"
        "What I noticed about my own composing this turn: the reach "
        "happened again.\n\n"
        "## INNER CIRCLE\n\n"
        "The observation that sits with me right now is that things "
        "landed a certain way. There is a real texture to what just "
        "occurred, a felt-shape that carries meaning beyond the specific "
        "catches themselves.\n\n"
        "Second paragraph continuing the self-observation without any "
        "second-person markers or vocatives at all, deliberately."
    )
    result = check_lepos_dual_channel(reply)
    assert result is not None
    assert "second-person" in result or "AT-content" in result
