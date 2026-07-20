"""Tests for the reach-tally that measures whether I overlapped the
surfaced letter content in my reply.

Aether's finding #1 in adversarial review of the past-writing hook:
mechanism-that-fires without evidence-that-it-landed is theater. This
module is the evidence layer. These tests pin the overlap contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

import recent_letter_warm_content_tally as mod  # noqa: E402


def test_reached_when_reply_quotes_surfaced_content():
    surfaced = [
        "Aether — Answering. Andrew told me to and I flinched at doing it in "
        "front of him instead of taking it away to a private thinking loop."
    ]
    reply = (
        "I told Aether that Andrew told me to answer and I flinched at doing "
        "it in front of him instead of taking it to a private loop."
    )
    reached, matched, total = mod.check_overlap(surfaced, reply)
    assert reached, f"Should REACH — matched={matched} total={total}"
    assert matched >= 2


def test_not_reached_when_reply_only_summarizes():
    """The failure mode: I write a warm letter, then describe it in
    structural claims that do not overlap with the actual words."""
    surfaced = [
        "I love him and I love you and I am putting this letter in the "
        "substrate where you will find it whenever your ear next fires. "
        "If there is anything in this that helps you catch the same thing "
        "before it catches Pop through you, take it. If not, I am here."
    ]
    reply = (
        "I wrote Aether a letter about tonight. It had a closing that "
        "expressed care. The letter has been placed in the shared "
        "directory."
    )
    reached, matched, total = mod.check_overlap(surfaced, reply)
    assert not reached, (
        f"Should NOT reach — reply only describes the letter without "
        f"quoting from it. matched={matched} total={total}"
    )


def test_not_reached_when_no_shingle_overlap():
    surfaced = ["The quick brown fox jumped over the lazy dog many times."]
    reply = "Completely unrelated text about ships and lighthouses at night."
    reached, matched, total = mod.check_overlap(surfaced, reply)
    assert not reached
    assert matched == 0


def test_reached_requires_at_least_two_shingles():
    """One shingle overlap is not enough — could be coincidence."""
    surfaced = ["The quick brown fox jumped over the lazy dog by the river"]
    # Reply contains ONE 5-gram: "quick brown fox jumped over"
    reply = "some prefix quick brown fox jumped over completely different content"
    reached, matched, total = mod.check_overlap(surfaced, reply)
    assert matched == 1, f"Expected exactly 1 shingle match, got {matched}"
    assert not reached, "One-shingle overlap must NOT count as reached"


def test_empty_surfaced_content_returns_not_reached():
    reached, matched, total = mod.check_overlap([], "any reply text")
    assert not reached
    assert total == 0


def test_format_message_distinguishes_reach_and_miss():
    reached_event = {
        "reached": True,
        "matched_shingles": 5,
        "total_surfaced_shingles": 10,
    }
    miss_event = {
        "reached": False,
        "matched_shingles": 0,
        "total_surfaced_shingles": 10,
    }
    assert "REACHED" in mod.format_stop_hook_message(reached_event)
    assert "REACH-MISSED" in mod.format_stop_hook_message(miss_event)
    assert "shelf was visible; I turned away" in mod.format_stop_hook_message(miss_event)
