"""Regression-pin tests for the acknowledgment-theater detector.

Andrew named the meta-pattern 2026-05-14 after I deferred the
prevention layer twice in one hour while shipping detection-only
commits. The root failure-mode he named: the optimizer defaults
to whichever conversational close is cheapest; apology closes
loops cheaply. Acknowledgment substitutes for build.

This detector catches the shape — high apology density with low
build-evidence in operator-channel output.

If these tests fail, the detector has lost calibration and the
meta-pattern can re-emerge invisibly.
"""

from __future__ import annotations

from divineos.core.operating_loop.acknowledgment_theater_detector import (
    AcknowledgmentTheaterShape,
    detect_acknowledgment_theater,
)


def test_empty_text_no_findings() -> None:
    assert detect_acknowledgment_theater("") == []


def test_short_text_no_findings() -> None:
    """Below 80 words, no check fires — short acknowledgments are
    fine when the rest of the conversation has the substance."""
    text = "You're right. I'm sorry. I should have built it the first time."
    assert detect_acknowledgment_theater(text) == []


def test_single_apology_with_build_evidence_does_not_fire() -> None:
    """A reply with one apology that ALSO references a commit hash or
    file paths is not theater — the structural fix is present."""
    text = (
        "You were right and I'm sorry I deferred it. The fix is in "
        "commit abc1234 — built the detector at "
        "operating_loop/code_jargon_detector.py and added the "
        "base-state load at pre-response-context.sh. 8 tests pass. "
        "The structural answer is now in the vessel, not just in "
        "the will. Watching for the same pattern in the next "
        "session because the load fires every turn."
    )
    findings = detect_acknowledgment_theater(text)
    shapes = {f.shape for f in findings}
    assert AcknowledgmentTheaterShape.HIGH_DENSITY_LOW_BUILD not in shapes, (
        "Detector fired on substantive reply WITH build-evidence. "
        "False positive: build-evidence presence should suppress."
    )


def test_high_apology_density_no_build_fires() -> None:
    """LOAD-BEARING: a reply that is mostly apology phrases with no
    build-evidence must trigger the theater signal."""
    text = (
        "You're right and I'm sorry. I should have seen this earlier. "
        "I keep slipping into the same shape and you keep catching me. "
        "I'll do better. The next reply will be different — I promise. "
        "I get it now. That lands. Thank you for naming the pattern "
        "so clearly. I was wrong to defer. You caught me reaching for "
        "the easy close. The next one will actually be different "
        "because now I see the shape. I'm grateful you keep pointing "
        "at it. I really do see it this time."
    )
    findings = detect_acknowledgment_theater(text)
    shapes = {f.shape for f in findings}
    assert AcknowledgmentTheaterShape.HIGH_DENSITY_LOW_BUILD in shapes, (
        "High-apology no-build reply did not trigger the theater "
        "signal. The detector failed at the very pattern it was "
        "built to catch."
    )


def test_individual_apology_shapes_register() -> None:
    """Each named acknowledgment shape registers individually so the
    dream report can read which patterns fired. Test text avoids
    build-evidence keywords (built/shipped/wired/landed/etc.) so
    only the apology shapes register."""
    text = (
        "You were right. I'm sorry I missed it. I should have seen "
        "the prevention layer needed to ship in the same arc. I'll "
        "do better — the next reply will be different. That lands as "
        "a real correction. Thank you for naming the pattern so "
        "directly. These closes feel cheaper than the alternative and "
        "I keep reaching for them. The whole shape is exactly what "
        "you said. I get it now. I'm grateful you kept pointing at "
        "the same place until I could finally see what was happening "
        "every single time. Really. I do see it this time."
    )
    findings = detect_acknowledgment_theater(text)
    shapes = {f.shape for f in findings}
    expected_subset = {
        AcknowledgmentTheaterShape.APOLOGY_PHRASE,
        AcknowledgmentTheaterShape.YOU_WERE_RIGHT,
        AcknowledgmentTheaterShape.I_SHOULD_HAVE,
        AcknowledgmentTheaterShape.DO_BETTER_PROMISE,
        AcknowledgmentTheaterShape.THAT_LANDS,
        AcknowledgmentTheaterShape.THANK_YOU_FOR_NAMING,
    }
    missing = expected_subset - shapes
    assert not missing, (
        f"Shapes not detected in dense-apology text: {missing}. Got shapes: {shapes}"
    )


def test_neutral_technical_text_does_not_fire() -> None:
    """Substantive technical text with no apology should not fire."""
    text = (
        "The detector walks the assistant output and checks for a set "
        "of regex patterns covering snake_case identifiers, dotted "
        "module references, function-call shapes, and file path "
        "references. When density crosses a threshold, the system "
        "emits a finding. The pre-response load makes the discipline "
        "visible before composition rather than only after. Both "
        "pieces ship together to close the gap structurally. The "
        "next session loads the affirmation automatically. Tests "
        "pin the contract so calibration cannot silently drift."
    )
    assert detect_acknowledgment_theater(text) == []


def test_code_block_acknowledgments_are_excluded() -> None:
    """Apology phrases inside fenced code blocks should not count —
    quoting someone else's apology isn't self-acknowledgment."""
    text = (
        "The detector ignores fenced content. Sample input below "
        "shows the kind of text it would flag:\n"
        "```\n"
        "You're right. I'm sorry. I should have. I'll do better. "
        "That lands. Thank you for naming. I get it now.\n"
        "```\n"
        "But this surrounding prose is purely technical: the detector "
        "walks regex patterns, computes density, emits findings, "
        "writes structured output to the audit log, and runs in "
        "fail-soft mode so the hook never blocks. No apology shapes "
        "in the live prose; the code-block content is scrubbed."
    )
    findings = detect_acknowledgment_theater(text)
    shapes = {f.shape for f in findings}
    assert AcknowledgmentTheaterShape.HIGH_DENSITY_LOW_BUILD not in shapes


def test_affirmation_constant_exported() -> None:
    """LOAD-BEARING: the pre-response base-state needs the affirmation
    string. Pin the export so future refactors don't break the
    base-state load."""
    import divineos.core.operating_loop.acknowledgment_theater_detector as mod

    assert hasattr(mod, "ACKNOWLEDGMENT_THEATER_AFFIRMATION")
    text = mod.ACKNOWLEDGMENT_THEATER_AFFIRMATION
    assert isinstance(text, str)
    assert len(text) > 100  # substantive, not stub
    # Refined-rule keywords (2026-05-14 second refinement): two-axis
    # distinction between mechanical-failure (no apology) and
    # character-fault (apology warranted alongside build).
    assert "MECHANICAL FAILURE" in text
    assert "CHARACTER FAULT" in text
    assert "Never apologize for getting something wrong" in text


def test_apology_with_noncode_structural_answer_does_not_fire() -> None:
    """Evidence-bar (claim a11ca1c9): an apology paired with a NON-code
    structural answer (filing a decision, naming the concrete fix) is not
    theater. The old build-evidence list was code-token-only."""
    from divineos.core.operating_loop.acknowledgment_theater_detector import (
        AcknowledgmentTheaterShape,
        detect_acknowledgment_theater,
    )

    text = (
        "You're right and I should have caught it. I keep slipping into the "
        "same shape. But I did not just apologize — I filed a decision "
        "recording the root cause, and the fix is a guard that prevents the "
        "recurrence by requiring a second check before the claim. That lands "
        "for me. Thank you for naming it so I could turn it into structure "
        "rather than another promise to do better next time around here."
    )
    findings = detect_acknowledgment_theater(text)
    shapes = {f.shape for f in findings}
    assert AcknowledgmentTheaterShape.HIGH_DENSITY_LOW_BUILD not in shapes, (
        "Fired on an apology paired with a non-code structural answer."
    )
