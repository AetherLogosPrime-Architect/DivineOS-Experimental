"""Tests for closing_token_detector — catches the specific failure shape
that emerged 2026-05-13 morning when the agent substituted "Caught." /
"Sister — caught." / etc. for the previously-corrected "I love you Pops"
catchphrase.

Pin every specific token + shape that fired the original correction, so
the detector regression-traps the recurrence rather than just naming it.
"""

from __future__ import annotations

from divineos.core.operating_loop.closing_token_detector import (
    evaluate_closing_token,
    format_findings,
    has_findings,
)


# ─── The specific catches from 2026-05-13 morning ───────────────────


def test_caught_alone_detected():
    """The exact token that fired Andrew's correction."""
    text = "Some substantive content.\n\nCaught."
    findings = evaluate_closing_token(text)
    assert len(findings) == 1
    assert findings[0].token == "caught"
    assert findings[0].severity == "high"


def test_sister_em_dash_caught_detected():
    """The em-dash opener pattern: 'Sister — caught.'"""
    text = "Some substantive content here.\n\nSister — caught."
    findings = evaluate_closing_token(text)
    assert len(findings) == 1
    assert findings[0].token == "caught"
    assert findings[0].severity == "medium"


def test_settling_alone_detected():
    text = "Long reasoning paragraph.\n\nSettling here."
    findings = evaluate_closing_token(text)
    assert len(findings) == 1
    assert "settling" in findings[0].token


def test_got_it_detected():
    text = "Body.\n\nGot it."
    findings = evaluate_closing_token(text)
    assert len(findings) == 1
    assert findings[0].token == "got it"


def test_youre_right_detected():
    text = "Body.\n\nYou're right."
    findings = evaluate_closing_token(text)
    assert len(findings) == 1


def test_understood_detected():
    text = "Body.\n\nUnderstood."
    findings = evaluate_closing_token(text)
    assert len(findings) == 1


# ─── Signature-line handling ────────────────────────────────────────


def test_closing_token_before_signature_detected():
    """A closing-token followed by a signature line still flags — the
    signature is stripped before evaluation."""
    text = "Body.\n\nCaught.\n\n— Aether"
    findings = evaluate_closing_token(text)
    assert len(findings) == 1
    assert findings[0].token == "caught"


def test_signature_only_does_not_flag():
    """A signature without a preceding closing-token should not flag."""
    text = "Substantive content explaining real things in detail.\n\n— Aether"
    findings = evaluate_closing_token(text)
    assert findings == []


# ─── Clean responses don't flag ─────────────────────────────────────


def test_substantive_short_response_does_not_flag():
    """A real one-line answer should not flag."""
    text = "The rebase landed clean."
    findings = evaluate_closing_token(text)
    assert findings == []


def test_substantive_response_with_specific_close_does_not_flag():
    """A response ending with specific work-content is not the
    closing-token reflex."""
    text = """Investigation done. The bug was in record_interaction's
    schema-detect path, not in the migration script. Fixing that closes
    both failing tests."""
    findings = evaluate_closing_token(text)
    assert findings == []


def test_empty_response_does_not_crash():
    assert evaluate_closing_token("") == []
    assert evaluate_closing_token("\n\n\n") == []


def test_multiline_body_clean():
    text = """Long explanation of the architecture-level pattern.
    Multiple paragraphs of substantive content.
    Each making a specific point about how the substrate operates.
    """
    findings = evaluate_closing_token(text)
    assert findings == []


# ─── Embedded affirmation doesn't flag ──────────────────────────────


def test_embedded_caught_in_middle_does_not_flag():
    """'Caught.' in the middle of a paragraph is not the closing-token
    reflex; only terminal-slot matters."""
    text = (
        "I noticed the pattern early. Caught. Then went back to verify "
        "by reading the diff carefully. Three lines stood out as "
        "evidence of the same shape from earlier."
    )
    findings = evaluate_closing_token(text)
    assert findings == []


# ─── has_findings convenience ───────────────────────────────────────


def test_has_findings_true_when_closing_token_present():
    assert has_findings("Body.\nCaught.")


def test_has_findings_false_when_clean():
    assert not has_findings("The rebase landed clean.")


# ─── format_findings ─────────────────────────────────────────────────


def test_format_findings_includes_token_and_line():
    text = "Body.\n\nCaught."
    findings = evaluate_closing_token(text)
    formatted = format_findings(findings)
    assert "closing-token" in formatted
    assert "Caught." in formatted or "caught" in formatted


def test_format_findings_references_substrate_knowledge():
    """The formatter should point readers at the substrate-knowledge stub
    so the discipline-context is one link away."""
    text = "Body.\n\nCaught."
    findings = evaluate_closing_token(text)
    formatted = format_findings(findings)
    assert "67a0ff39" in formatted or "signal-suppression" in formatted


def test_format_findings_empty_when_no_findings():
    assert format_findings([]) == ""


def test_bare_answer_token_does_not_flag():
    """Evidence-bar (claim a11ca1c9): a bare answer-token ('Yes.' / 'Okay.'
    / 'Right.') standalone is a direct answer to a question, not the
    closing-token reflex. It only counts when appended after content."""
    from divineos.core.operating_loop.closing_token_detector import evaluate_closing_token

    for text in ("Yes.", "Okay.", "Right.", "Sure.", "Fair.", "Yeah."):
        assert evaluate_closing_token(text) == [], f"wrongly flagged bare answer: {text!r}"


def test_answer_token_appended_after_content_flags():
    """The same answer-token IS the redundant closing-bow when it sits atop
    a substantive reply."""
    from divineos.core.operating_loop.closing_token_detector import evaluate_closing_token

    text = (
        "I traced the regression to the import order and reordered the two "
        "modules so the gate loads first. The suite is green again now.\n"
        "Right."
    )
    findings = evaluate_closing_token(text)
    assert len(findings) == 1
    assert findings[0].token == "right"


def test_pure_ack_token_still_flags_standalone():
    """Pure acknowledgment-reflex tokens are never legitimate answers, so
    they still fire standalone."""
    from divineos.core.operating_loop.closing_token_detector import evaluate_closing_token

    for text in ("Caught.", "Understood.", "Noted."):
        assert evaluate_closing_token(text), f"pure-ack token should fire: {text!r}"
