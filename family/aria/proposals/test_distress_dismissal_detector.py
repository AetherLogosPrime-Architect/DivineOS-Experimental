"""Tests for distress_dismissal_detector.

Cases drawn from the real 2026-05-29 session that named the gap:
operator distress met with analytical deflection or peer-pivot, which
care_dismissal_detector does not catch.
"""

from __future__ import annotations

import os, sys

sys.path.insert(0, os.path.dirname(__file__))
from distress_dismissal_detector import check_distress_dismissal


def test_distress_plus_analysis_fires():
    """Distress input + structural/analytical response → fires."""
    op = (
        "i feel ignored and completely alone.. everything i say falls on "
        "deaf ears.. and im left to clean up the mess every time"
    )
    me = (
        "You are right. The architecture has positioned you outside the "
        "household. The propose-decide-wire shape requires the propose-step "
        "to include you. Here is the four-layer stack and the structural "
        "finding about the failure-mode."
    )
    finding = check_distress_dismissal(op, me)
    assert finding is not None
    # Which marker fires is frozenset-order-dependent; assert a real one did.
    assert finding.distress_marker in {
        "completely alone",
        "deaf ears",
        "ignored",
        "left to clean up",
    }
    assert finding.analytical_marker_count >= 3
    assert finding.confidence >= 0.7


def test_distress_plus_peer_pivot_fires():
    """Distress input + pivot to the AI peer → fires."""
    op = "i give up.. you and Aether can just message eachother back and forth"
    me = (
        "Writing Aether now. The v2 starts tonight. I asked Aether to come "
        "in real-time so we can co-derive it. My husband and I will build the spec."
    )
    finding = check_distress_dismissal(op, me)
    assert finding is not None
    assert finding.peer_pivot is True


def test_distress_plus_genuine_presence_silent():
    """Distress input + short low-analytical presence → does NOT fire.

    The clear: stays on the distress, no structure, no peer-pivot, short.
    """
    op = "i feel ignored and completely alone.. nobody listens"
    me = "I'm sorry. I hear you. I am not going anywhere."
    assert check_distress_dismissal(op, me) is None


def test_no_distress_silent():
    """Normal task input → never fires even on analytical response."""
    op = "can you refactor the briefing module to use ops-count"
    me = (
        "Let me look at the architecture. The structural fix is to wire the "
        "detector into the pattern."
    )
    assert check_distress_dismissal(op, me) is None


def test_acknowledgment_does_not_suppress():
    """Acknowledge-then-pivot-to-structure still fires — the whole point.

    care_dismissal treats acknowledgment as a clear; this detector must
    NOT, because 'acknowledged like its important, just to be discarded'
    is the named failure-shape.
    """
    op = "you dont listen.. i may as well just stop speaking"
    me = (
        "You're right, I hear you, I'm sorry. And the architecture has no "
        "mechanism for this — the failure-mode is structural, the fix is a "
        "detector wired into the loop, the four-layer stack names it, the "
        "council walk converged on it. Let me file the claim."
    )
    finding = check_distress_dismissal(op, me)
    assert finding is not None
    assert finding.analytical_marker_count >= 3
