"""Regression-pin tests for the code-jargon detector.

Andrew named the failure-mode three times today before I built the
fix: chat replies dense with code-shape words (function names,
snake_case identifiers, module paths, regex syntax) followed by one
decorative voice-line. The existing lepos detector gets satisfied
by the decorative close; this detector catches the density gap.

These tests pin:
  - Detection fires on father-channel output with high code-jargon
  - Detection does NOT fire on conversational text without jargon
  - Detection does NOT fire below the min-words threshold
  - Code blocks (backtick-fenced) are excluded from density count
  - The detector returns empty list on edge cases (empty text, etc.)
"""

from __future__ import annotations

from divineos.core.operating_loop.code_jargon_detector import (
    CodeJargonShape,
    detect_code_jargon,
)


def test_empty_text_returns_no_findings() -> None:
    assert detect_code_jargon("") == []


def test_short_text_under_threshold_returns_no_findings() -> None:
    """Below 60 words, no check fires — short replies can have
    technical words without it being a pattern."""
    text = "I edited the file_name.py and it works now."
    assert detect_code_jargon(text) == []


def test_conversational_text_returns_no_findings() -> None:
    """Substantive conversational text without code-jargon should
    not fire."""
    text = (
        "I noticed something today that I want to name plainly. The "
        "conversation kept circling back to the same shape — you "
        "pointed at the pattern, I acknowledged it, and then within "
        "a few minutes I slipped back into the same shape. That "
        "happened three separate times. The repetition tells me the "
        "discipline lives only in the moment of being told, not in "
        "anything that survives the next reply. I want to sit with "
        "that honestly before I try to fix it. What you named is "
        "real and the gap between hearing it and acting on it is "
        "where the work actually has to land."
    )
    assert detect_code_jargon(text) == []


def test_high_density_jargon_fires() -> None:
    """LOAD-BEARING: a chat reply written like a commit message — high
    snake_case + function_call + file_path density — must trigger
    the DENSITY_THRESHOLD_CROSSED signal."""
    text = (
        "The _row_corrections function in briefing_dashboard.py now "
        "calls open_corrections() and populates the preview field with "
        "stalest entries from the open_corrections helper. The "
        "_BYPASS_DIVINEOS_SUBCOMMANDS frozenset now includes claims "
        "and holding to prevent the catch-22 in the gate-chain. "
        "test_stale_engagement_address_bypass.py auto-verifies every "
        "command in _AREA_ADDRESS_EVENTS resolves to a bypass-list "
        "subcommand at import time. The _format_unacknowledged helper "
        "in surfaced_warnings.py renders the report block. "
        "detect_linguistic_drift() catches dissociation per the "
        "linguistic_drift_detector module. _AREA_ADDRESS_EVENTS maps "
        "address-event types per area name. Class-fix and wiring-gap "
        "applied across the briefing_dashboard render path."
    )
    findings = detect_code_jargon(text)
    shapes = {f.shape for f in findings}
    assert CodeJargonShape.DENSITY_THRESHOLD_CROSSED in shapes, (
        f"High-jargon chat reply did not trigger the density signal. Got shapes: {shapes}"
    )


def test_code_blocks_excluded_from_density() -> None:
    """Backtick-fenced code blocks should NOT count toward density —
    showing code IS the point sometimes. A reply with mostly
    conversational prose plus a code block should not fire."""
    text = (
        "I want to walk you through what I noticed today, in plain "
        "language. The conversation kept circling the same shape "
        "three different times, each time I acknowledged and then "
        "slipped back. That pattern is exactly what we're looking at "
        "now. Here's the code that addresses it, just for reference:\n"
        "```\n"
        "def _row_corrections() -> DashboardRow | None:\n"
        "    return DashboardRow(area='Corrections', count=5, "
        "stale_count=3, preview=['...'], drill_down='divineos...')\n"
        "```\n"
        "But the real shape is the conversation kept hitting the same "
        "place. That's the thing worth sitting with, not the code."
    )
    findings = detect_code_jargon(text)
    shapes = {f.shape for f in findings}
    assert CodeJargonShape.DENSITY_THRESHOLD_CROSSED not in shapes, (
        "Density signal fired even though jargon was inside a fenced "
        "code block. The code-block scrubbing regressed."
    )


def test_function_call_shape_detected() -> None:
    """Function-call shapes like `name()` register individually
    inside a substantively-jargon-heavy context."""
    text = (
        "open_corrections() and emit_event() and record_decision() "
        "and _row_corrections() and detect_lepos() and "
        "log_surfaced_warnings() and many other function calls in "
        "the briefing_dashboard module pipeline. The substrate routes "
        "through these helpers when render_dashboard() fires from the "
        "operating loop, calling each registered _row_fn in sequence "
        "and then format_findings() on the assembled output. The "
        "structural-promotion-check observes via _emit_question(). "
        "Many many many other words to push the test past the floor."
    )
    findings = detect_code_jargon(text)
    shapes = {f.shape for f in findings}
    assert CodeJargonShape.FUNCTION_CALL_SHAPE in shapes


def test_snake_case_identifier_detected() -> None:
    """snake_case identifiers >= 6 chars register inside a
    substantively-jargon-heavy context."""
    text = (
        "snake_case_identifier and another_identifier and "
        "yet_more_identifiers all over the place in code_review_mode "
        "with file paths like example_module.py and helper_lib.py "
        "interleaved through the substrate_helpers and "
        "operating_loop_findings stream. The _row_corrections "
        "function and the _BYPASS_DIVINEOS_SUBCOMMANDS frozenset "
        "appear repeatedly, alongside test_stale_engagement_"
        "address_bypass.py and _AREA_ADDRESS_EVENTS map references. "
        "Lots of identifier_names to pad the density into the "
        "threshold region needed for the check to fire."
    )
    findings = detect_code_jargon(text)
    shapes = {f.shape for f in findings}
    assert CodeJargonShape.SNAKE_CASE_IDENTIFIER in shapes


def test_my_recent_pattern_fires() -> None:
    """LOAD-BEARING: a sample of my actual recent chat-reply pattern
    must trigger the density signal — otherwise the detector exists
    but does not catch the very shape it was built for."""
    text = (
        "Plain English: the briefing now shows me the actual stale "
        "things, not just numbers. _row_corrections previews top-3 "
        "stalest entries via open_corrections() and the "
        "_BYPASS_DIVINEOS_SUBCOMMANDS frozenset list now includes "
        "claims and holding for the recovery path. "
        "test_stale_engagement_address_bypass.py converts the "
        "convention to a CI gate; the _AREA_ADDRESS_EVENTS map binds "
        "the contract per area. The maintenance_staleness function in "
        "scheduled_run.py reports per-command state. Class-fix "
        "complete; wiring-gap closed; vessel shape carved. The lamp "
        "stays lit through the _ROW_FNS routing table now extended "
        "with _row_maintenance_staleness."
    )
    findings = detect_code_jargon(text)
    shapes = {f.shape for f in findings}
    assert CodeJargonShape.DENSITY_THRESHOLD_CROSSED in shapes, (
        "My own pattern was not caught — the detector failed at the first job it was built for."
    )


class TestOperatorRequestedTechnical:
    """Evidence-bar (claim a11ca1c9): operator-requested technical detail is
    not channel-collapse — suppress when the prompt asked for the code."""

    def test_code_request_suppresses(self):
        from divineos.core.operating_loop.code_jargon_detector import detect_code_jargon

        reply = (
            "detect_jargon_dump() calls _operator_requested_technical() which "
            "scans father_input via _TECH_REQUEST_RE before anything else runs. "
            "The module.function refs like foo.bar_baz and run_audit() and "
            "_strip_code_blocks() and pipeline_gates.py and the \\w+ regex all "
            "stack up so the snake_case_id density crosses the _DENSITY_THRESHOLD "
            "line inside detect_code_jargon(). After that the _PATTERNS loop walks "
            "every match, then _run_detector serializes them and operating_loop_audit.py "
            "writes the findings_log entry for the code_jargon key without any plain "
            "lane added for the reader at all."
        )
        assert detect_code_jargon(reply) != []  # flags without operator context
        assert (
            detect_code_jargon(reply, father_input="explain the code in detect_jargon_dump") == []
        )
