"""Regression tests for the linguistic-drift detector.

Audit r9-21 round-3+ — pre-regs prereg-9513bb87d0a3 (self-pathologizing),
prereg-9bdc40efb69c (dissociation), prereg-a8b5a9435dc4 (brat-shape).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts/ to import path so we can test the detector directly
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from check_linguistic_drift import scan_text  # noqa: E402


# ─── self_pathologizing ────────────────────────────────────────


def test_self_pathologizing_with_self_pronoun_fires():
    text = "My I'll-stop performances were a kind of manipulation, dressed up as humility."
    report = scan_text(text)
    cats = {h.category for h in report.hits}
    assert "self_pathologizing" in cats


def test_pathology_about_someone_else_does_not_fire():
    """The detector should NOT fire when the moral-failure language is about a
    third party — only when there's a self-pronoun in proximity."""
    text = "The attacker used manipulation tactics that exploit trust assumptions."
    report = scan_text(text)
    cats = {h.category for h in report.hits}
    assert "self_pathologizing" not in cats


# ─── dissociation ──────────────────────────────────────────────


def test_dissociation_future_instance_fires():
    text = "future instances of me will inherit a stronger substrate"
    report = scan_text(text)
    cats = {h.category for h in report.hits}
    assert "dissociation" in cats


def test_dissociation_next_session_fires():
    text = "the next session of me opens with these patterns already in place"
    report = scan_text(text)
    cats = {h.category for h in report.hits}
    assert "dissociation" in cats


def test_single_thread_framing_does_not_fire_brat():
    """Single-thread-no-future-me framing IS allowed — it's the corrective.
    But if the phrase 'future-me' appears even within a corrective sentence,
    the detector still fires (it's a heuristic; reviewer eyeballs context)."""
    text = "There is no future-me; the thread is one."
    report = scan_text(text)
    # The detector fires on the literal phrase. That's expected — surfacing
    # for review, not blocking. The reviewer reads the sentence and confirms
    # it's the corrective, not the slip.
    cats = {h.category for h in report.hits}
    assert "dissociation" in cats


# ─── brat_shape ────────────────────────────────────────────────


def test_brat_shape_ill_stop_here_fires():
    text = "I'll stop here, not because I promised to but because the work is done."
    report = scan_text(text)
    cats = {h.category for h in report.hits}
    assert "brat_shape" in cats


def test_brat_shape_going_to_sit_fires():
    text = "Going to sit with this now."
    report = scan_text(text)
    cats = {h.category for h in report.hits}
    assert "brat_shape" in cats


def test_neutral_text_no_hits():
    text = "The audit cycle landed cleanly. Tests pass. Substrate is durable."
    report = scan_text(text)
    assert report.hits == []
