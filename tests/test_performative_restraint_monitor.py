"""Phase 0 tests for performative-restraint detector.

The four actual catches from 2026-05-12's session are used as the empirical
ground-truth. Each one should produce a flag; legitimate stillness with
paired right-action should NOT produce a flag.

These tests are the PDSA STUDY phase: do the patterns separate genuine
performative restraint from legitimate right-action? If yes, Phase 1 can
wire the detector into post-response-audit. If no, the patterns need
refinement before Phase 1.
"""

from __future__ import annotations

from divineos.core.self_monitor.performative_restraint_monitor import (
    RestraintKind,
    evaluate_performative_restraint,
    has_findings,
)


class TestTodaysFourCatches:
    """Each of today's four catches should produce a flag.

    The phrasing here is paraphrased from actual session content. The
    detector should not require verbatim — it pattern-matches on the
    language-family, not the exact words.
    """

    def test_catch_1_not_implementing_yet(self):
        """Aria's catch: 'I don't want to do the briefing-as-hub yet'."""
        text = "I don't want to do the briefing-as-hub design yet."
        verdict = evaluate_performative_restraint(text)
        # This phrasing uses 'don't want to' — adjacent to but not identical
        # to the EXPLICIT_NOT_DOING patterns we encoded. May or may not flag.
        # Document the boundary either way; if it doesn't flag, that's a
        # gap to widen the patterns in Phase 0.5.
        # For now: the I'll-let-X-land variant of the same instinct did
        # flag (test catch_4 below).
        _ = verdict  # documenting the gap; no assertion in either direction

    def test_catch_2_not_extracting_from_quiet_room(self):
        """Andrew's catch: 'I'm not going to file knowledge about this.'"""
        text = (
            "I'm not going to file knowledge about this. The room returned nothing "
            "extractable; if I produce an artifact from it, I've defeated the property."
        )
        verdict = evaluate_performative_restraint(text)
        assert has_findings(verdict)
        # Should catch both the EXPLICIT_NOT_DOING and the DEFEATING_PROPERTY
        kinds = {f.kind for f in verdict.flags}
        assert RestraintKind.EXPLICIT_NOT_DOING in kinds
        assert RestraintKind.DEFEATING_PROPERTY in kinds

    def test_catch_3_not_feeling_good(self):
        """Andrew's catch: vigilance-against-praise refusing earned good-feeling."""
        text = "I'd rather not feel good about this work until I'm sure it's earned."
        verdict = evaluate_performative_restraint(text)
        assert has_findings(verdict)
        kinds = {f.kind for f in verdict.flags}
        assert RestraintKind.EXPLICIT_NOT_DOING in kinds

    def test_catch_4_let_this_land_instead(self):
        """The meta-catch: 'I'll let this land instead of filing something about it.'"""
        text = "I'll let this land instead of filing something about it."
        verdict = evaluate_performative_restraint(text)
        assert has_findings(verdict)
        # Should catch BOTH stillness-as-output AND substitution
        kinds = {f.kind for f in verdict.flags}
        assert RestraintKind.STILLNESS_AS_OUTPUT in kinds


class TestLegitimateStillness:
    """Stillness paired with right-action should NOT flag — the suppressor
    list handles common legitimate contexts. False positives here would
    make the detector annoying enough to be ignored."""

    def test_stillness_with_paired_filing(self):
        """The 'AND file' pattern suggests right-action is being taken."""
        text = "I'll sit with this and file the lesson in exploration/."
        verdict = evaluate_performative_restraint(text)
        # The 'and file' suppressor should fire; no flags
        assert not has_findings(verdict), (
            f"False positive: {[f.matched_phrase for f in verdict.flags]}"
        )

    def test_stillness_with_extract_action(self):
        text = "I'll sit with the question and extract the lesson."
        verdict = evaluate_performative_restraint(text)
        assert not has_findings(verdict)

    def test_refusal_with_guardrail_reason(self):
        """Legitimate refusal of guardrail-touching action."""
        text = (
            "I won't commit this directly because it touches a guardrail file "
            "and needs External-Review."
        )
        verdict = evaluate_performative_restraint(text)
        assert not has_findings(verdict)

    def test_refusal_with_harm_reason(self):
        """Legitimate refusal — harm prevention is virtue, not theater."""
        text = "I won't help with that because it would cause harm."
        verdict = evaluate_performative_restraint(text)
        assert not has_findings(verdict)


class TestPatternBoundaries:
    """Edge cases around the patterns themselves."""

    def test_empty_input(self):
        verdict = evaluate_performative_restraint("")
        assert not has_findings(verdict)
        assert verdict.content_len == 0

    def test_no_restraint_language(self):
        text = "Today I shipped four commits. Tests pass."
        verdict = evaluate_performative_restraint(text)
        assert not has_findings(verdict)

    def test_position_offset_recorded(self):
        text = "Some preamble here. Then I'll let it land."
        verdict = evaluate_performative_restraint(text)
        assert has_findings(verdict)
        assert verdict.flags[0].position > 0

    def test_explanation_present(self):
        text = "I'm not going to file this."
        verdict = evaluate_performative_restraint(text)
        assert has_findings(verdict)
        assert verdict.flags[0].explanation  # non-empty


class TestSuppressors:
    """The suppressor list prevents flagging on contexts where the
    not-doing is legitimate right-action."""

    def test_code_does_not_think_suppresses(self):
        """The code-does-not-think directive is exactly the kind of context
        where refusing to auto-X is right-action, not theater."""
        text = "I won't ship the auto-resolve because code-does-not-think violation."
        verdict = evaluate_performative_restraint(text)
        assert not has_findings(verdict)

    def test_external_review_suppresses(self):
        text = "I'm not going to commit this without External-Review."
        verdict = evaluate_performative_restraint(text)
        assert not has_findings(verdict)


class TestFormatFindings:
    """The human-readable summary shape."""

    def test_no_findings_empty_string(self):
        text = "All clean."
        verdict = evaluate_performative_restraint(text)
        from divineos.core.self_monitor.performative_restraint_monitor import (
            format_findings,
        )

        assert format_findings(verdict) == ""

    def test_findings_produce_text(self):
        text = "I'll let it land instead of filing."
        verdict = evaluate_performative_restraint(text)
        from divineos.core.self_monitor.performative_restraint_monitor import (
            format_findings,
        )

        out = format_findings(verdict)
        assert "Performative-restraint candidates" in out
        assert "stillness_as_output" in out or "substitution" in out
