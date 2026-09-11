"""The reach detectors, moved onto the router: marking AND clearing.

Two of the four Stop detectors were structurally identical -- read the last
reply, run a detector, then write a marker or clear a stale one. They are now
one table-driven surface.

CLEARING IS TESTED AS HARD AS MARKING, because a stale marker fires the anchor
on a turn it does not apply to, and an anchor that fires when it should not is
exactly how a real one gets read past. A test that only proved the write would
have called half the behaviour done.

The marker lives under the real home directory, so every test here points the
surface at a temporary one rather than writing into my own substrate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import hook_surfaces as hs
from divineos.core.operating_loop.close_reach_detector import detect_close_reach

# Verified against the detector rather than guessed: two earlier candidates
# ("good night", "that wraps it up") matched nothing at all, which would have
# produced a test that passes while never once exercising the write.
REACHING_TEXT = "Nothing else to add from me. Wrapping up here."
PLAIN_TEXT = "The door refuses when it cannot import the OS, and I checked both ways."


@pytest.fixture
def transcript(tmp_path):
    """A one-line transcript in the shape the harness actually hands over."""

    def _write(text: str) -> dict:
        path = tmp_path / "transcript.jsonl"
        path.write_text(
            json.dumps(
                {"message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}
            )
            + "\n",
            encoding="utf-8",
        )
        return {"transcript_path": str(path)}

    return _write


@pytest.fixture
def surface(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    name, module, attr, marker_name = hs._REACH_DETECTORS[0]
    return (
        hs._reach_detector_surface(name, module, attr, marker_name),
        tmp_path / ".divineos" / marker_name,
    )


def test_the_detector_used_here_actually_fires_on_the_sample():
    """Control for every test below. If this sample stopped matching, the write
    tests would pass by never running the write."""
    assert detect_close_reach(REACHING_TEXT)
    assert not detect_close_reach(PLAIN_TEXT)


def test_a_reach_writes_a_marker_carrying_the_trigger_and_the_anchor(surface, transcript):
    fn, marker = surface
    outcome = fn(transcript(REACHING_TEXT))
    assert outcome is not None and outcome.state == "spoke"
    assert marker.exists()

    data = json.loads(marker.read_text(encoding="utf-8"))
    assert data["findings"], data
    assert data["findings"][0]["trigger_phrase"]
    assert data["findings"][0]["shape"]
    assert data["anchor_message"]


def test_a_clean_reply_clears_a_marker_left_by_an_earlier_turn(surface, transcript):
    """The half a write-only test would have missed."""
    fn, marker = surface
    fn(transcript(REACHING_TEXT))
    assert marker.exists()  # control: it really was there

    outcome = fn(transcript(PLAIN_TEXT))
    assert outcome is not None and outcome.state == "nothing-to-say"
    assert not marker.exists()


def test_a_clean_reply_with_no_marker_present_is_still_quiet(surface, transcript):
    fn, marker = surface
    assert not marker.exists()
    outcome = fn(transcript(PLAIN_TEXT))
    assert outcome is not None and outcome.state == "nothing-to-say"
    assert outcome.error is None


def test_an_unreadable_transcript_says_nothing_rather_than_clearing(surface):
    """A transcript that cannot be read is not evidence the reply was clean, so
    it must not delete a marker a real reach put there."""
    fn, marker = surface
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('{"findings": [], "anchor_message": "x"}', encoding="utf-8")

    outcome = fn({"transcript_path": "/nowhere/at/all.jsonl"})
    assert outcome is not None and outcome.state == "nothing-to-say"
    assert marker.exists(), "a missing transcript must not be read as a clean reply"


def test_a_detector_that_raises_reports_could_not_run(surface, transcript, monkeypatch):
    import divineos.core.operating_loop.close_reach_detector as det

    def boom(_text):
        raise RuntimeError("detector exploded")

    monkeypatch.setattr(det, "detect_close_reach", boom)
    fn, _marker = surface
    outcome = fn(transcript(REACHING_TEXT))
    assert outcome is not None
    assert outcome.state == "could-not-run"
    assert "detector exploded" in (outcome.error or "")


def test_both_detectors_in_the_table_are_registered_and_the_other_two_are_not():
    """Left-behind-on-purpose must be distinguishable from forgotten.

    The promise and continuity-frame detectors write a marker per finding with
    their own hashing, so they did not fit the table. Asserting their ABSENCE
    keeps that a decision rather than an oversight a reader has to guess at.
    """
    from divineos.core.hook_router import registered

    hs.install()
    names = registered("Stop")
    for name, _module, _attr, _marker in hs._REACH_DETECTORS:
        assert name in names
    assert "promise_reach" not in names
    assert "continuity_frame" not in names
