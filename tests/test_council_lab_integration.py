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
    def test_chaos_triggers_lc(self) -> None:
        pairs = detect_triggers("How does this system behave near chaos?")
        assert pairs == [("LC", "chaos")]

    def test_entropy_triggers_lc(self) -> None:
        pairs = detect_triggers("What is the entropy of this distribution?")
        assert pairs == [("LC", "entropy")]

    def test_no_trigger_on_unrelated_problem(self) -> None:
        assert detect_triggers("How do I cook pasta al dente?") == []

    def test_one_term_triggers_once_despite_multiple_words(self) -> None:
        # Both 'chaos' and 'entropy' are LC triggers; should fire once.
        pairs = detect_triggers("chaos and entropy and bounded disorder")
        assert len(pairs) == 1
        assert pairs[0][0] == "LC"

    def test_case_insensitive(self) -> None:
        assert detect_triggers("CHAOS") == [("LC", "chaos")]

    def test_punctuation_stripped(self) -> None:
        assert detect_triggers("Is this chaos?") == [("LC", "chaos")]

    def test_substring_does_not_match(self) -> None:
        # 'chaotic' IS a trigger; 'chromebook' should not match 'chaos'.
        # (Guarding against accidental substring matching.)
        assert detect_triggers("chromebook configuration") == []

    def test_balance_triggers_omegab(self) -> None:
        pairs = detect_triggers("Does this system stay in balance?")
        assert ("OmegaB", "balance") in pairs

    def test_both_terms_trigger_independently(self) -> None:
        # A problem touching chaos (LC) and probability (OmegaB) should
        # trigger both.
        pairs = detect_triggers("chaos and probability together")
        terms = {t for t, _ in pairs}
        assert "LC" in terms
        assert "OmegaB" in terms

    def test_observer_triggers_psi(self) -> None:
        pairs = detect_triggers("Role of the observer in this system")
        assert ("Psi", "observer") in pairs

    def test_measurement_triggers_psi(self) -> None:
        pairs = detect_triggers("How does measurement work here?")
        assert ("Psi", "measurement") in pairs

    def test_resonance_triggers_v(self) -> None:
        pairs = detect_triggers("How does resonance shape this?")
        assert ("V", "resonance") in pairs

    def test_lorentz_triggers_a(self) -> None:
        pairs = detect_triggers("Apply Lorentz factor here")
        assert ("A", "lorentz") in pairs

    def test_gravity_triggers_f(self) -> None:
        pairs = detect_triggers("What is the role of gravity?")
        assert ("F", "gravity") in pairs


class TestGatherLabEvidence:
    def test_evidence_attached_when_triggered(self) -> None:
        evidence = gather_lab_evidence("Analyze chaos in this system")
        assert len(evidence) == 1
        assert evidence[0].term == "LC"
        assert evidence[0].trigger == "chaos"
        assert evidence[0].result["term"] == "LC"
        assert evidence[0].summary.startswith("LC:")

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

    def test_convene_attaches_evidence_on_trigger(self) -> None:
        engine = self._engine()
        result = engine.convene("Analyze the chaos in this system")
        assert len(result.lab_evidence) == 1
        assert result.lab_evidence[0].term == "LC"
        assert "Lab evidence" in result.synthesis

    def test_convene_no_evidence_on_non_trigger(self) -> None:
        engine = self._engine()
        result = engine.convene("Should I ship this feature?")
        assert result.lab_evidence == []
        assert "Lab evidence" not in result.synthesis

    def test_use_lab_false_disables_evidence(self) -> None:
        engine = self._engine()
        result = engine.convene("Analyze the chaos in this system", use_lab=False)
        assert result.lab_evidence == []
        assert "Lab evidence" not in result.synthesis

    def test_single_lens_still_gets_evidence(self) -> None:
        engine = CouncilEngine()
        engine.register(_toy_expert("Solo"))
        result = engine.convene("Bounded entropy discussion")
        assert len(result.lab_evidence) == 1
        assert "Lab evidence" in result.synthesis
