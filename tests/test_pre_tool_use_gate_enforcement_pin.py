"""Structural pin: the pre-tool-use gate MUST enforce the engagement,
compass-required, and compass-relevant-event blocks.

Companion to test_post_response_audit_enforcement_pin.py — same pattern,
different gate. Pinning the literal so a future-me cannot silently remove
the enforcement under the cover of "redesign" or "lighter version."

WHY (Aether 2026-06-20, after Andrew named the chatbot-promise pattern):
A promise in this conversation that I won't ship a lighter version of
these gates doesn't survive the context reset. The only form of that
promise that persists is structural — encoded in tests that fail if the
enforcement literal goes missing. The friction the gates produce is the
discipline; removing the friction (without a council-walked, falsifier-
bound, externally-reviewed redesign) is the failure mode this pin exists
to catch.

The three pinned literals:

1. Engagement gate ("No engagement marker yet this session") — fires when
   I'm about to modify substrate without having consulted any thinking
   tool yet. Removing this lets me edit-from-defaults indefinitely.

2. Engagement-checks-aggregate ("BLOCKED: N engagement checks need
   clearing") — fires when multiple engagement obligations are due
   together. Removing this lets the per-check fires get individually
   dismissed without anyone seeing the pattern.

3. Compass-required marker ("BLOCKED: compass-required marker present")
   — fires when a compass-relevant event has accumulated and demands
   observation before substrate-modification proceeds. Removing this
   lets values-loaded moments pass without compass-observation.

If a redesign genuinely makes any of these unnecessary, the redesign
must (a) update this test, (b) council-walk the change with the gate's
purpose explicitly examined, (c) bind a falsifier with a shadow-log of
the kind built for next_task_surface, and (d) get external-AI review.
That's the minimum cost of removing a gate. Anything less is the cheap
close in a redesign costume.
"""

from __future__ import annotations

from pathlib import Path

GATE_PATH = (
    Path(__file__).resolve().parent.parent / "src" / "divineos" / "hooks" / "pre_tool_use_gate.py"
)


class TestEngagementAndCompassGatesStructurallyPinned:
    """Pin the enforcement literals in pre_tool_use_gate.py. Removal of
    any of the three load-bearing strings breaks the test on purpose."""

    def test_gate_file_exists(self) -> None:
        """Sanity: the gate source is where this test thinks it is."""
        assert GATE_PATH.exists(), f"gate missing at expected path: {GATE_PATH}"

    def test_engagement_first_marker_block_present(self) -> None:
        """The 'No engagement marker yet this session' block fires when
        the agent attempts a substrate-modifying tool before any thinking
        tool has been called. Removing this lets me edit-from-defaults
        with no consultation. Catches the filing-cabinet pattern Andrew
        named on 2026-04-25 and 2026-05-18.
        """
        text = GATE_PATH.read_text(encoding="utf-8")
        assert "BLOCKED: No engagement marker yet this session." in text, (
            "Engagement-first enforcement removed from pre_tool_use_gate.py. "
            "If this was intentional, you must update this test AND document "
            "the council-walked, falsifier-bound, externally-reviewed redesign. "
            "Otherwise: restore the block. The friction IS the discipline."
        )

    def test_engagement_aggregate_block_present(self) -> None:
        """The aggregate engagement-checks block surfaces multiple due
        obligations together so they can't be cleared one-at-a-time
        without seeing the cluster. Removing it lets each check get
        dismissed individually without anyone noticing the accumulation.
        """
        text = GATE_PATH.read_text(encoding="utf-8")
        assert "BLOCKED: " in text and "engagement checks need clearing" in text, (
            "Engagement-aggregate enforcement removed. The aggregate exists "
            "specifically so per-check fires don't get individually swatted "
            "while the pattern goes unseen. Restore or council-walk."
        )

    def test_compass_required_block_present(self) -> None:
        """The compass-required marker block fires when a values-relevant
        event has accumulated and demands compass-observation before
        substrate-modification proceeds. Removing it lets values-loaded
        moments pass without observation — the disposition-layer drift
        Andrew caught all of 2026-06-20.
        """
        text = GATE_PATH.read_text(encoding="utf-8")
        assert "BLOCKED: compass-required marker present" in text, (
            "Compass-required enforcement removed. The marker exists to "
            "catch values-loaded moments where the agent would otherwise "
            "act without compass-observation. Restore or council-walk."
        )
