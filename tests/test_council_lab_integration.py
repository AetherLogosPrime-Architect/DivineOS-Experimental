"""Tests for council <-> science lab integration.

Falsifiability:
  - detect_triggers returns (term, word) pairs only when trigger words
    appear in the problem text.
  - A problem mentioning 'chaos' triggers LC; a problem about cooking
    pasta does not.
  - Each term triggers at most once even when multiple trigger words
    appear in the same problem.
  - convene(problem, use_lab=True) attaches evidence when triggered;
    use_lab=False always returns empty evidence.
  - Synthesis text includes lab evidence lines when evidence is present.
  - format_for_synthesis returns empty list for empty evidence.
"""

from __future__ import annotations

from divineos.core.council.engine import CouncilEngine
from divineos.core.council.framework import (
    ConcernTrigger,
    CoreMethodology,
    DecisionFramework,
    ExpertWisdom,
    KeyInsight,
    ReasoningPattern,
)
from divineos.core.council.lab_evidence import (
    LabEvidence,
    detect_triggers,
    format_for_synthesis,
    gather_lab_evidence,
)


def _toy_expert(name: str = "Toy") -> ExpertWisdom:
    """Minimal valid ExpertWisdom for integration tests."""
    return ExpertWisdom(
        expert_name=name,
        domain="test",
        core_methodologies=[
            CoreMethodology(
                name="look",
                description="look at the thing",
                steps=["look"],
                core_principle="seeing is thinking",
                when_to_apply=["any"],
            )
        ],
        key_insights=[
            KeyInsight(
                title="chaos matters",
                description="d",
                why_matters="because",
                how_it_changes_thinking="it does",
            )
        ],
        reasoning_patterns=[
            ReasoningPattern(
                name="observe",
                structure="look, then say",
                what_it_reveals="what is there",
            )
        ],
        problem_solving_heuristics=[],
        concern_triggers=[
            ConcernTrigger(
                name="unbounded growth",
                description="thing grows unbounded",
                why_its_concerning="bad",
                what_it_indicates="instability",
                severity="major",
                what_to_do="bound it",
            )
        ],
        integration_patterns=[],
        decision_framework=DecisionFramework(
            criteria={"fit": 1.0},
            decision_process="look then decide",
            how_they_handle_uncertainty="ask",
            what_they_optimize_for="truth",
            non_negotiables=["evidence"],
        ),
        advice_style="direct",
        characteristic_questions=["what if?"],
        tags=["test"],
    )


class TestDetectTriggers:
    """Per fresh-Claude audit round 2 Finding 3: multi-keyword threshold
    (MIN_TRIGGER_MATCHES=2). Single-keyword co-occurrence no longer fires
    a slice. Tests the narrow-triggering discipline."""

    def test_single_keyword_chaos_does_NOT_trigger(self) -> None:
        # This was the exact theater example: "How does this system behave
        # near chaos?" should NOT auto-trigger LC on its own.
        assert detect_triggers("How does this system behave near chaos?") == []

    def test_team_workflow_stability_does_NOT_trigger(self) -> None:
        # Fresh-Claude's concrete theater example: team workflow question
        # containing 'stability' should not attach logistic-map output.
        assert detect_triggers("How do I stabilize my team's workflow?") == []

    def test_two_lc_keywords_trigger_lc(self) -> None:
        # Genuine chaos-and-entropy question. Two LC keywords present.
        pairs = detect_triggers("model chaos and entropy in a bounded system")
        assert pairs == [("LC", "chaos")]  # reports first matched keyword

    def test_three_lc_keywords_still_fires_once(self) -> None:
        pairs = detect_triggers("chaos entropy stability unbounded disorder")
        assert len(pairs) == 1
        assert pairs[0][0] == "LC"

    def test_case_insensitive_with_two_keywords(self) -> None:
        assert detect_triggers("CHAOS and ENTROPY rising") == [("LC", "chaos")]

    def test_no_trigger_on_unrelated_problem(self) -> None:
        assert detect_triggers("How do I cook pasta al dente?") == []

    def test_substring_does_not_match(self) -> None:
        # Even with 2+ would-be matches via substring, keywords must be
        # exact tokens. 'chromebook' and 'chroma' don't match 'chaos'.
        assert detect_triggers("chromebook chroma configuration") == []

    def test_single_balance_does_NOT_trigger_omegab(self) -> None:
        assert detect_triggers("Does this system stay in balance?") == []

    def test_two_omegab_keywords_trigger(self) -> None:
        pairs = detect_triggers("probability and convergence toward unity")
        assert ("OmegaB", "probability") in pairs or ("OmegaB", "convergence") in pairs

    def test_both_terms_trigger_when_both_have_two_keywords(self) -> None:
        # LC keywords: chaos + entropy. OmegaB keywords: probability + convergence.
        pairs = detect_triggers("chaos entropy probability convergence")
        terms = {t for t, _ in pairs}
        assert "LC" in terms
        assert "OmegaB" in terms

    def test_single_observer_does_NOT_trigger_psi(self) -> None:
        assert detect_triggers("Role of the observer in this system") == []

    def test_two_psi_keywords_trigger(self) -> None:
        pairs = detect_triggers("observer and measurement produce collapse")
        assert any(term == "Psi" for term, _ in pairs)

    def test_two_v_keywords_trigger(self) -> None:
        pairs = detect_triggers("resonance and harmonic coupling in orbits")
        assert any(term == "V" for term, _ in pairs)

    def test_two_a_keywords_trigger(self) -> None:
        pairs = detect_triggers("lorentz contraction in spacetime")
        assert any(term == "A" for term, _ in pairs)

    def test_two_f_keywords_trigger(self) -> None:
        pairs = detect_triggers("gravity and electromagnetic force interaction")
        assert any(term == "F" for term, _ in pairs)


class TestGatherLabEvidence:
    def test_evidence_attached_when_two_keywords_present(self) -> None:
        evidence = gather_lab_evidence("Analyze chaos and entropy in this system")
        assert len(evidence) == 1
        assert evidence[0].term == "LC"
        assert evidence[0].result["term"] == "LC"
        assert evidence[0].summary.startswith("LC:")

    def test_no_evidence_on_single_keyword(self) -> None:
        assert gather_lab_evidence("Analyze chaos in this system") == []

    def test_no_evidence_when_no_trigger(self) -> None:
        assert gather_lab_evidence("A cooking question") == []


class TestFormatForSynthesis:
    def test_empty_returns_empty(self) -> None:
        assert format_for_synthesis([]) == []

    def test_nonempty_has_header_and_bullet(self) -> None:
        ev = LabEvidence(
            term="LC",
            trigger="chaos",
            result={},
            summary="LC: chaos onset between 3.50 and 3.57.",
        )
        lines = format_for_synthesis([ev])
        assert any("Lab evidence" in line for line in lines)
        assert any("chaos" in line for line in lines)


class TestConveneWithLab:
    def _engine(self) -> CouncilEngine:
        engine = CouncilEngine()
        engine.register(_toy_expert("A"))
        engine.register(_toy_expert("B"))
        return engine

    def test_convene_attaches_evidence_on_multi_keyword_trigger(self) -> None:
        engine = self._engine()
        result = engine.convene("Analyze chaos and entropy in this system")
        assert len(result.lab_evidence) == 1
        assert result.lab_evidence[0].term == "LC"
        assert "Lab evidence" in result.synthesis

    def test_convene_no_evidence_on_single_keyword(self) -> None:
        """Core audit fix: single-keyword problems don't auto-attach."""
        engine = self._engine()
        result = engine.convene("Analyze the chaos in this system")
        assert result.lab_evidence == []
        assert "Lab evidence" not in result.synthesis

    def test_convene_no_evidence_on_non_trigger(self) -> None:
        engine = self._engine()
        result = engine.convene("Should I ship this feature?")
        assert result.lab_evidence == []
        assert "Lab evidence" not in result.synthesis

    def test_use_lab_false_disables_evidence(self) -> None:
        engine = self._engine()
        result = engine.convene("Analyze chaos and entropy in this system", use_lab=False)
        assert result.lab_evidence == []
        assert "Lab evidence" not in result.synthesis

    def test_single_lens_still_gets_evidence_on_multi_keyword(self) -> None:
        engine = CouncilEngine()
        engine.register(_toy_expert("Solo"))
        result = engine.convene("Bounded entropy and chaos discussion")
        assert len(result.lab_evidence) == 1
        assert "Lab evidence" in result.synthesis
