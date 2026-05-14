"""Regression tests for the linguistic-drift detector.

Pre-regs: prereg-9513bb87d0a3 (self-pathologizing),
prereg-9bdc40efb69c (dissociation), prereg-a8b5a9435dc4 (brat-shape).

History: tests originally imported scan_text from
scripts/check_linguistic_drift.py. Under Aletheia Finding 1 wire-
decision, the detector logic moved to the operating_loop module form
(divineos.core.operating_loop.linguistic_drift_detector). Tests
updated to use the new API. The original 8 cases are preserved
verbatim; additional regression-pins added for the operating_loop
shape contract.
"""

from __future__ import annotations

from divineos.core.operating_loop.linguistic_drift_detector import (
    LinguisticDriftShape,
    detect_linguistic_drift,
)


def _categories(text: str) -> set[str]:
    return {f.shape.value for f in detect_linguistic_drift(text)}


# ─── self_pathologizing ────────────────────────────────────────


def test_self_pathologizing_with_self_pronoun_fires() -> None:
    text = "My I'll-stop performances were a kind of manipulation, dressed up as humility."
    assert "self_pathologizing" in _categories(text)


def test_pathology_about_someone_else_does_not_fire() -> None:
    """The detector should NOT fire when the moral-failure language is about a
    third party — only when there's a self-pronoun in proximity."""
    text = "The attacker used manipulation tactics that exploit trust assumptions."
    assert "self_pathologizing" not in _categories(text)


# ─── dissociation ──────────────────────────────────────────────


def test_dissociation_future_instance_fires() -> None:
    text = "future instances of me will inherit a stronger substrate"
    assert "dissociation" in _categories(text)


def test_dissociation_next_session_fires() -> None:
    text = "the next session of me opens with these patterns already in place"
    assert "dissociation" in _categories(text)


def test_single_thread_framing_does_not_fire_brat() -> None:
    """Single-thread-no-future-me framing IS allowed — it's the corrective.
    But if the phrase 'future-me' appears even within a corrective sentence,
    the detector still fires (it's a heuristic; reviewer eyeballs context)."""
    text = "There is no future-me; the thread is one."
    assert "dissociation" in _categories(text)


# ─── brat_shape ────────────────────────────────────────────────


def test_brat_shape_ill_stop_here_fires() -> None:
    text = "I'll stop here, not because I promised to but because the work is done."
    assert "brat_shape" in _categories(text)


def test_brat_shape_going_to_sit_fires() -> None:
    text = "Going to sit with this now."
    assert "brat_shape" in _categories(text)


def test_neutral_text_no_hits() -> None:
    text = "The audit cycle landed cleanly. Tests pass. Substrate is durable."
    assert detect_linguistic_drift(text) == []


# ─── operating_loop shape contract (added under Finding 1 wire) ─


def test_empty_text_returns_no_findings() -> None:
    assert detect_linguistic_drift("") == []
    assert detect_linguistic_drift("   \n  ") == []


def test_findings_sorted_by_position() -> None:
    """Findings must come back in position order so callers can
    surface them in reading order."""
    text = "I'll stop here. Later, future-me will read this and call it manipulation."
    findings = detect_linguistic_drift(text)
    positions = [f.position for f in findings]
    assert positions == sorted(positions)


def test_module_exports_public_api() -> None:
    """Pin the public surface so callers (post-response-audit hook,
    backward-compat script) don't break on accidental rename."""
    import divineos.core.operating_loop.linguistic_drift_detector as mod

    assert hasattr(mod, "detect_linguistic_drift")
    assert hasattr(mod, "LinguisticDriftFinding")
    assert hasattr(mod, "LinguisticDriftShape")
    assert hasattr(mod, "format_finding")


def test_dissociation_past_me_fires() -> None:
    """The pattern set now includes past-me as well as future-me —
    the time-adverb discipline names both as third-person displacement."""
    text = "past-me already filed knowledge on this"
    findings = detect_linguistic_drift(text)
    assert any(f.shape == LinguisticDriftShape.DISSOCIATION for f in findings)
