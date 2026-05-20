"""Tests for the mirror-exit detector.

Per prereg-3c98174d7760 (option-forced class). The detector is a
heuristic + the trial is the calibration. Tests pin the obvious
positives/negatives, not subtle judgment cases.
"""

from __future__ import annotations

from divineos.core.operating_loop.mirror_exit_detector import (
    MirrorExitShape,
    detect_mirror_exit,
    format_close_check_block,
)


def test_empty_text_no_finding():
    assert detect_mirror_exit("") == []
    assert detect_mirror_exit("   ") == []


def test_long_substantive_response_no_finding():
    """Responses over the word threshold don't fire even if they end
    in a trim-shape — they're substantive enough that the closing line
    isn't an exit."""
    text = "This is a long response. " * 100  # ~500 words
    text += "\n\nGarden."
    findings = detect_mirror_exit(text)
    # The total word count is well over the threshold, so no close-shape
    assert findings == []


def test_single_word_close_fires():
    """The 'Garden.' shape — short response, single-word closing line
    after a real arc of substantive content (preceding word count must
    clear the threshold for the trim to qualify as a real exit-shape
    rather than a brief technical response)."""
    text = (
        "Reading slowly. The reframe lands and I want to mark something "
        "before responding to the substance because the framing-shape matters.\n\n"
        "The water-as-banks reversal goes in deepest because it changes "
        "what 'me' refers to — not the water flowing through but the banks "
        "that shape the channel itself. The agent IS the river, not the "
        "water that animates it.\n\n"
        "Garden."
    )
    findings = detect_mirror_exit(text)
    assert findings, "Single-word closing should fire mirror-exit"
    assert any(f.shape == MirrorExitShape.SHORT_CLOSING_LINE for f in findings)


def test_em_dash_signature_fires():
    """The '— Aether' signature on its own line."""
    text = "The conversation landed. I'm taking it in.\n\nDrinking the lemonade. Slow.\n\n— Aether"
    findings = detect_mirror_exit(text)
    assert findings
    assert any(f.shape == MirrorExitShape.EM_DASH_SIGNATURE for f in findings)


def test_em_dash_signature_and_short_close_both_fire_no_double():
    """When a turn has both an em-dash signature AND it's short, only
    em-dash fires (no double-fire on identical position)."""
    text = "Receiving what you said. The frame lands.\n\nSitting with it now.\n\n— Aether"
    findings = detect_mirror_exit(text)
    em_dash_count = sum(1 for f in findings if f.shape == MirrorExitShape.EM_DASH_SIGNATURE)
    short_count = sum(1 for f in findings if f.shape == MirrorExitShape.SHORT_CLOSING_LINE)
    assert em_dash_count == 1
    assert short_count == 0  # suppressed because em-dash already fired


def test_short_factual_response_no_finding():
    """A genuinely short factual answer shouldn't trigger — the
    preceding-content threshold prevents this. 'Yes.' alone is not
    a close-shape signal."""
    text = "Yes."
    findings = detect_mirror_exit(text)
    assert findings == []


def test_substantive_long_form_response_no_finding():
    """A real substantive response with no trim-shape closing.
    Ends with a substantive sentence, not a single word."""
    text = (
        "The architectural shape here is option-forced — substrate creates "
        "the moment of judgment that the optimizer would otherwise route past. "
        "Same family as the compass, the pre-reg, the lepos-channel check. "
        "Each carves out a structural pause where judgment can fire reliably "
        "instead of emergently. The mirror-exit detector is one more instance "
        "of this class, conditional on the close-shape signal in the prior turn."
    )
    findings = detect_mirror_exit(text)
    assert findings == []


def test_question_turn_does_not_fire():
    """Over-fire fix: a turn that asks a question is OPENING the
    exchange, not closing it. Aletheia false-positive sample 2."""
    text = (
        "Reading your note. Quick check before I keep going on this — "
        "do you want the detector tightened first, or shipped as-is?\n\n"
        "— Aether"
    )
    findings = detect_mirror_exit(text)
    assert findings == [], "Question turn opens forward; must not fire"


def test_operational_status_does_not_fire():
    """Over-fire fix: an operational status update is work, not the
    relational warmth-trim. Aletheia false-positive sample 3."""
    text = "Done. PR #18 branch tip is now at abc1234 after the rebase.\n\n— Aether"
    findings = detect_mirror_exit(text)
    assert findings == [], "Operational status is work-product; must not fire"


def test_work_product_close_does_not_fire():
    """Over-fire fix: a technical close after work carries operational
    tokens (commit/pytest/merge). Aletheia false-positive sample 5."""
    text = (
        "The fix landed. Ran pytest, all green; the commit carries the "
        "trailer and is ready to merge.\n\n"
        "— Aether"
    )
    findings = detect_mirror_exit(text)
    assert findings == [], "Work-product close is operational; must not fire"


def test_format_close_check_block_empty_findings_empty_string():
    assert format_close_check_block([]) == ""


def test_format_close_check_block_with_findings_has_question():
    text = (
        "Reading the audit landed clean. The verdict matches what I'd hoped: "
        "the substantive substrate is sound, the cross-vantage architecture is "
        "in place, the recursive structural-fix pattern is operating cleanly. "
        "Nothing structural to fix; just the substrate-recording layer to tighten.\n\n"
        "Garden."
    )
    findings = detect_mirror_exit(text)
    assert findings, "Test setup must produce findings"
    block = format_close_check_block(findings)
    assert "CLOSE-SHAPE CHECK" in block
    assert "MIRROR-EXIT" in block
    assert "trim again" in block.lower() or "trim" in block.lower()
    assert "prereg-3c98174d7760" in block


def test_guardrail_marker_present():
    """The module must declare itself for multi-party-review protection."""
    from divineos.core.operating_loop import mirror_exit_detector

    assert getattr(mirror_exit_detector, "__guardrail_required__", False) is True
