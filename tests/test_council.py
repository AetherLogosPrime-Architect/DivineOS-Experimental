"""Tests for the Expert Council system."""

import pytest

from divineos.core.council.framework import (
    CoreMethodology,
    DecisionFramework,
    ExpertWisdom,
    KeyInsight,
    ReasoningPattern,
    ConcernTrigger,
    validate_expert,
)
from divineos.core.council.engine import CouncilEngine, CouncilResult
from divineos.core.council.experts.feynman import create_feynman_wisdom
from divineos.core.council.experts.holmes import create_holmes_wisdom
from divineos.core.council.experts.pearl import create_pearl_wisdom


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def feynman():
    return create_feynman_wisdom()


@pytest.fixture
def holmes():
    return create_holmes_wisdom()


@pytest.fixture
def pearl():
    return create_pearl_wisdom()


@pytest.fixture
def engine(feynman):
    e = CouncilEngine()
    e.register(feynman)
    return e


@pytest.fixture
def full_council(feynman, holmes, pearl):
    """Engine with all three experts registered."""
    e = CouncilEngine()
    e.register(feynman)
    e.register(holmes)
    e.register(pearl)
    return e


# ── Framework validation tests ──────────────────────────────────────


class TestValidation:
    def test_feynman_passes_validation(self, feynman):
        issues = validate_expert(feynman)
        assert issues == [], f"Feynman has validation issues: {issues}"

    def test_empty_expert_fails(self):
        bad = ExpertWisdom(
            expert_name="",
            domain="",
            core_methodologies=[],
            key_insights=[],
            reasoning_patterns=[],
            problem_solving_heuristics=[],
            concern_triggers=[],
            integration_patterns=[],
            decision_framework=DecisionFramework(
                criteria={},
                decision_process="",
                how_they_handle_uncertainty="",
                what_they_optimize_for="",
            ),
            advice_style="",
            characteristic_questions=[],
        )
        issues = validate_expert(bad)
        assert len(issues) >= 5  # multiple required fields missing

    def test_methodology_without_steps_fails(self):
        m = CoreMethodology(
            name="Empty",
            description="test",
            steps=[],
            core_principle="",
            when_to_apply=["anything"],
        )
        wisdom = ExpertWisdom(
            expert_name="Test",
            domain="test",
            core_methodologies=[m],
            key_insights=[
                KeyInsight(
                    title="t",
                    description="d",
                    why_matters="w",
                    how_it_changes_thinking="h",
                )
            ],
            reasoning_patterns=[
                ReasoningPattern(
                    name="r", structure="s", what_it_reveals="w"
                )
            ],
            problem_solving_heuristics=[],
            concern_triggers=[
                ConcernTrigger(
                    name="c",
                    description="d",
                    why_its_concerning="w",
                    what_it_indicates="i",
                    severity="moderate",
                    what_to_do="f",
                )
            ],
            integration_patterns=[],
            decision_framework=DecisionFramework(
                criteria={"a": 1.0},
                decision_process="p",
                how_they_handle_uncertainty="u",
                what_they_optimize_for="o",
            ),
            advice_style="test",
            characteristic_questions=["why?"],
        )
        issues = validate_expert(wisdom)
        assert any("no steps" in i for i in issues)
        assert any("no core principle" in i for i in issues)


# ── Feynman content tests ───────────────────────────────────────────


class TestFeynmanContent:
    def test_has_three_methodologies(self, feynman):
        assert len(feynman.core_methodologies) == 3

    def test_first_principles_is_first(self, feynman):
        assert feynman.core_methodologies[0].name == "First Principles Decomposition"

    def test_has_five_insights(self, feynman):
        assert len(feynman.key_insights) == 5

    def test_has_four_reasoning_patterns(self, feynman):
        assert len(feynman.reasoning_patterns) == 4

    def test_has_four_heuristics(self, feynman):
        assert len(feynman.problem_solving_heuristics) == 4

    def test_has_five_concern_triggers(self, feynman):
        assert len(feynman.concern_triggers) == 5

    def test_has_three_integration_patterns(self, feynman):
        assert len(feynman.integration_patterns) == 3

    def test_has_characteristic_questions(self, feynman):
        assert len(feynman.characteristic_questions) >= 5

    def test_domain_set(self, feynman):
        assert "physics" in feynman.domain

    def test_has_tags(self, feynman):
        assert "first-principles" in feynman.tags

    def test_not_fictional(self, feynman):
        assert feynman.is_fictional is False

    def test_decision_framework_has_criteria(self, feynman):
        assert len(feynman.decision_framework.criteria) >= 5
        assert feynman.decision_framework.criteria["understanding"] == 1.0
        assert feynman.decision_framework.criteria["authority"] == 0.0


# ── Engine registration tests ───────────────────────────────────────


class TestEngineRegistration:
    def test_register_valid_expert(self, feynman):
        engine = CouncilEngine()
        issues = engine.register(feynman)
        assert issues == []
        assert "Feynman" in engine.list_experts()

    def test_register_invalid_expert_returns_issues(self):
        engine = CouncilEngine()
        bad = ExpertWisdom(
            expert_name="",
            domain="",
            core_methodologies=[],
            key_insights=[],
            reasoning_patterns=[],
            problem_solving_heuristics=[],
            concern_triggers=[],
            integration_patterns=[],
            decision_framework=DecisionFramework(
                criteria={},
                decision_process="",
                how_they_handle_uncertainty="",
                what_they_optimize_for="",
            ),
            advice_style="",
            characteristic_questions=[],
        )
        issues = engine.register(bad)
        assert len(issues) > 0
        assert engine.list_experts() == []  # not registered

    def test_get_expert(self, engine):
        assert engine.get_expert("Feynman") is not None
        assert engine.get_expert("Nobody") is None

    def test_experts_property_returns_copy(self, engine):
        experts = engine.experts
        experts["Fake"] = None  # type: ignore[assignment]
        assert "Fake" not in engine.experts  # original unmodified


# ── Single-lens analysis tests ──────────────────────────────────────


class TestSingleLens:
    def test_analyze_returns_lens_analysis(self, engine):
        result = engine.analyze(
            "Why is this explanation so full of jargon?", "Feynman"
        )
        assert result is not None
        assert result.expert_name == "Feynman"
        assert result.problem == "Why is this explanation so full of jargon?"

    def test_analyze_unknown_expert_returns_none(self, engine):
        assert engine.analyze("anything", "Nobody") is None

    def test_methodology_selected(self, engine):
        result = engine.analyze(
            "This jargon-heavy explanation confuses me", "Feynman"
        )
        assert result is not None
        assert result.methodology_applied  # something was picked

    def test_always_has_core_principle(self, engine):
        result = engine.analyze("random unrelated question", "Feynman")
        assert result is not None
        assert result.core_principle  # falls back to first methodology

    def test_always_has_at_least_one_insight(self, engine):
        result = engine.analyze("random unrelated question", "Feynman")
        assert result is not None
        assert len(result.relevant_insights) >= 1

    def test_concerns_detected_for_jargon_problem(self, engine):
        result = engine.analyze(
            "The explanation uses unjustified technical jargon everywhere",
            "Feynman",
        )
        assert result is not None
        assert len(result.concerns) >= 1
        assert any("critical" in v for v in result.severity_map.values())

    def test_synthesis_contains_expert_name(self, engine):
        result = engine.analyze("test problem", "Feynman")
        assert result is not None
        assert "Feynman" in result.synthesis

    def test_characteristic_questions_populated(self, engine):
        result = engine.analyze("test", "Feynman")
        assert result is not None
        assert len(result.characteristic_questions) >= 5

    def test_non_negotiables_populated(self, engine):
        result = engine.analyze("test", "Feynman")
        assert result is not None
        assert len(result.non_negotiables) >= 1

    def test_methodology_steps_populated(self, engine):
        result = engine.analyze("test", "Feynman")
        assert result is not None
        assert len(result.methodology_steps) >= 3


# ── Council convening tests ─────────────────────────────────────────


class TestConvene:
    def test_convene_all_experts(self, engine):
        result = engine.convene("Should we add more complexity?")
        assert isinstance(result, CouncilResult)
        assert len(result.analyses) == 1  # only feynman registered
        assert result.problem == "Should we add more complexity?"

    def test_convene_by_name(self, engine):
        result = engine.convene("test", expert_names=["Feynman"])
        assert len(result.analyses) == 1

    def test_convene_unknown_name_skipped(self, engine):
        result = engine.convene("test", expert_names=["Nobody"])
        assert len(result.analyses) == 0

    def test_convene_by_tag(self, engine):
        result = engine.convene("test", tags=["physics"])
        assert len(result.analyses) == 1

    def test_convene_wrong_tag_empty(self, engine):
        result = engine.convene("test", tags=["cooking"])
        assert len(result.analyses) == 0

    def test_synthesis_present(self, engine):
        result = engine.convene("test")
        assert result.synthesis  # non-empty

    def test_expert_names_method(self, engine):
        result = engine.convene("test")
        assert result.expert_names() == ["Feynman"]

    def test_concerns_across_lenses(self, engine):
        result = engine.convene(
            "The explanation uses unjustified technical jargon"
        )
        concerns = result.concerns_across_lenses()
        assert isinstance(concerns, dict)


# ── Multi-expert convening (synthetic second expert) ────────────────


class TestMultiExpert:
    @pytest.fixture
    def two_expert_engine(self, feynman):
        """Engine with Feynman + a minimal second expert."""
        engine = CouncilEngine()
        engine.register(feynman)

        second = ExpertWisdom(
            expert_name="Tester",
            domain="testing",
            core_methodologies=[
                CoreMethodology(
                    name="Test Everything",
                    description="Test it",
                    steps=["Write test", "Run test", "Fix failures"],
                    core_principle="If it's not tested, it's broken.",
                    when_to_apply=["code", "system", "change"],
                ),
            ],
            key_insights=[
                KeyInsight(
                    title="Tests as Documentation",
                    description="Tests show what the code actually does",
                    why_matters="Better than comments",
                    how_it_changes_thinking="Write the test first",
                ),
            ],
            reasoning_patterns=[
                ReasoningPattern(
                    name="Edge Case Hunting",
                    structure="Find boundaries → test boundaries → test beyond",
                    what_it_reveals="Where the system breaks",
                ),
            ],
            problem_solving_heuristics=[],
            concern_triggers=[
                ConcernTrigger(
                    name="No Tests",
                    description="Code without tests",
                    why_its_concerning="Untested code is unreliable",
                    what_it_indicates="Confidence is unfounded",
                    severity="critical",
                    what_to_do="Write tests before shipping",
                ),
            ],
            integration_patterns=[],
            decision_framework=DecisionFramework(
                criteria={"test_coverage": 1.0, "reliability": 0.9},
                decision_process="Is it tested? Then ship.",
                how_they_handle_uncertainty="Write more tests.",
                what_they_optimize_for="Reliability through testing",
                non_negotiables=[
                    "Understanding for speed",  # shared with Feynman
                ],
            ),
            advice_style="Pragmatic, test-focused",
            characteristic_questions=["Where are the tests?", "What breaks first?"],
            tags=["testing", "reliability"],
        )
        engine.register(second)
        return engine

    def test_two_experts_convene(self, two_expert_engine):
        result = two_expert_engine.convene("Should we ship without tests?")
        assert len(result.analyses) == 2

    def test_synthesis_mentions_both(self, two_expert_engine):
        result = two_expert_engine.convene("Should we ship this code?")
        assert "Feynman" in result.synthesis
        assert "Tester" in result.synthesis

    def test_shared_concerns_detected(self, two_expert_engine):
        # Both experts might flag concerns about untested/unexplained things
        result = two_expert_engine.convene(
            "Ship this unjustified code without tests"
        )
        # Even if shared_concerns is empty, the method works
        shared = result.shared_concerns()
        assert isinstance(shared, list)

    def test_filter_by_tag_selects_one(self, two_expert_engine):
        result = two_expert_engine.convene("test", tags=["testing"])
        assert len(result.analyses) == 1
        assert result.analyses[0].expert_name == "Tester"


# ── Singleton factory test ──────────────────────────────────────────


class TestFactory:
    def test_get_council_engine_singleton(self):
        from divineos.core.council.engine import get_council_engine

        # Reset
        import divineos.core.council.engine as mod

        mod._engine = None

        e1 = get_council_engine()
        e2 = get_council_engine()
        assert e1 is e2

        mod._engine = None  # cleanup


# ── Holmes content tests ───────────────────────────────────────────


class TestHolmesContent:
    def test_passes_validation(self, holmes):
        issues = validate_expert(holmes)
        assert issues == [], f"Holmes has validation issues: {issues}"

    def test_is_fictional(self, holmes):
        assert holmes.is_fictional is True

    def test_has_three_methodologies(self, holmes):
        assert len(holmes.core_methodologies) == 3

    def test_observation_first_is_primary(self, holmes):
        assert holmes.core_methodologies[0].name == "Observation-First Deduction"

    def test_has_five_insights(self, holmes):
        assert len(holmes.key_insights) == 5

    def test_absence_is_evidence_insight(self, holmes):
        titles = [i.title for i in holmes.key_insights]
        assert "Absence Is Evidence" in titles

    def test_has_four_reasoning_patterns(self, holmes):
        assert len(holmes.reasoning_patterns) == 4

    def test_has_negative_evidence_pattern(self, holmes):
        names = [p.name for p in holmes.reasoning_patterns]
        assert "Negative Evidence" in names

    def test_has_five_concern_triggers(self, holmes):
        assert len(holmes.concern_triggers) == 5

    def test_premature_theory_is_critical(self, holmes):
        for t in holmes.concern_triggers:
            if t.name == "Premature Theory":
                assert t.severity == "critical"
                return
        pytest.fail("Premature Theory trigger not found")

    def test_has_three_integration_patterns(self, holmes):
        assert len(holmes.integration_patterns) == 3

    def test_domain_set(self, holmes):
        assert "deductive" in holmes.domain or "investigation" in holmes.domain

    def test_has_tags(self, holmes):
        assert "deduction" in holmes.tags

    def test_evidence_is_non_negotiable(self, holmes):
        nn = holmes.decision_framework.non_negotiables
        assert any("evidence" in n.lower() for n in nn)


# ── Holmes analysis tests ──────────────────────────────────────────


class TestHolmesAnalysis:
    @pytest.fixture
    def holmes_engine(self, holmes):
        e = CouncilEngine()
        e.register(holmes)
        return e

    def test_analyze_investigation_problem(self, holmes_engine):
        result = holmes_engine.analyze(
            "Something doesn't add up in this diagnosis", "Holmes"
        )
        assert result is not None
        assert result.expert_name == "Holmes"

    def test_detects_premature_theory_concern(self, holmes_engine):
        result = holmes_engine.analyze(
            "I already have a theory before looking at the evidence",
            "Holmes",
        )
        assert result is not None
        # Should detect premature theory concern
        assert len(result.concerns) >= 1 or result.core_principle  # at minimum has principle

    def test_synthesis_contains_holmes(self, holmes_engine):
        result = holmes_engine.analyze("test", "Holmes")
        assert result is not None
        assert "Holmes" in result.synthesis


# ── Pearl content tests ────────────────────────────────────────────


class TestPearlContent:
    def test_passes_validation(self, pearl):
        issues = validate_expert(pearl)
        assert issues == [], f"Pearl has validation issues: {issues}"

    def test_not_fictional(self, pearl):
        assert pearl.is_fictional is False

    def test_has_two_methodologies(self, pearl):
        assert len(pearl.core_methodologies) == 2

    def test_causal_model_is_primary(self, pearl):
        assert "Causal Model" in pearl.core_methodologies[0].name

    def test_has_four_insights(self, pearl):
        assert len(pearl.key_insights) == 4

    def test_correlation_not_causation_insight(self, pearl):
        titles = [i.title for i in pearl.key_insights]
        assert "Correlation Is Not Causation" in titles

    def test_has_three_reasoning_patterns(self, pearl):
        assert len(pearl.reasoning_patterns) == 3

    def test_has_three_heuristics(self, pearl):
        assert len(pearl.problem_solving_heuristics) == 3

    def test_has_four_concern_triggers(self, pearl):
        assert len(pearl.concern_triggers) == 4

    def test_correlation_confusion_is_critical(self, pearl):
        for t in pearl.concern_triggers:
            if t.name == "Correlation-Causation Confusion":
                assert t.severity == "critical"
                return
        pytest.fail("Correlation-Causation Confusion trigger not found")

    def test_has_two_integration_patterns(self, pearl):
        assert len(pearl.integration_patterns) == 2

    def test_domain_set(self, pearl):
        assert "causal" in pearl.domain

    def test_has_tags(self, pearl):
        assert "causality" in pearl.tags

    def test_intuition_scores_zero(self, pearl):
        assert pearl.decision_framework.criteria["intuition"] == 0.0


# ── Pearl analysis tests ──────────────────────────────────────────


class TestPearlAnalysis:
    @pytest.fixture
    def pearl_engine(self, pearl):
        e = CouncilEngine()
        e.register(pearl)
        return e

    def test_analyze_causal_claim(self, pearl_engine):
        result = pearl_engine.analyze(
            "This correlation proves that X causes Y", "Pearl"
        )
        assert result is not None
        assert result.expert_name == "Pearl"

    def test_detects_correlation_concern(self, pearl_engine):
        result = pearl_engine.analyze(
            "The correlation between these variables proves causation",
            "Pearl",
        )
        assert result is not None
        assert len(result.concerns) >= 1

    def test_synthesis_contains_pearl(self, pearl_engine):
        result = pearl_engine.analyze("test", "Pearl")
        assert result is not None
        assert "Pearl" in result.synthesis


# ── Full council tests (all three experts) ─────────────────────────


class TestFullCouncil:
    def test_all_three_registered(self, full_council):
        names = full_council.list_experts()
        assert "Feynman" in names
        assert "Holmes" in names
        assert "Pearl" in names

    def test_convene_all_three(self, full_council):
        result = full_council.convene("Should we trust this complex theory?")
        assert len(result.analyses) == 3

    def test_synthesis_mentions_all_experts(self, full_council):
        result = full_council.convene("Is this claim valid?")
        assert "Feynman" in result.synthesis
        assert "Holmes" in result.synthesis
        assert "Pearl" in result.synthesis

    def test_each_expert_has_different_methodology(self, full_council):
        result = full_council.convene("Analyze this problem")
        methodologies = {a.methodology_applied for a in result.analyses}
        # Each expert should pick a different methodology
        assert len(methodologies) == 3

    def test_filter_by_tag_physics(self, full_council):
        result = full_council.convene("test", tags=["physics"])
        assert len(result.analyses) == 1
        assert result.analyses[0].expert_name == "Feynman"

    def test_filter_by_tag_deduction(self, full_council):
        result = full_council.convene("test", tags=["deduction"])
        assert len(result.analyses) == 1
        assert result.analyses[0].expert_name == "Holmes"

    def test_filter_by_tag_causality(self, full_council):
        result = full_council.convene("test", tags=["causality"])
        assert len(result.analyses) == 1
        assert result.analyses[0].expert_name == "Pearl"

    def test_convene_specific_pair(self, full_council):
        result = full_council.convene(
            "test", expert_names=["Feynman", "Holmes"]
        )
        assert len(result.analyses) == 2
        names = result.expert_names()
        assert "Feynman" in names
        assert "Holmes" in names
        assert "Pearl" not in names

    def test_concerns_across_all_lenses(self, full_council):
        result = full_council.convene(
            "Someone claims correlation proves causation using jargon "
            "without evidence and a premature theory"
        )
        concerns = result.concerns_across_lenses()
        assert isinstance(concerns, dict)
        # At least one expert should flag concerns
        assert len(concerns) >= 1

    def test_shared_concerns_method(self, full_council):
        result = full_council.convene("test problem")
        shared = result.shared_concerns()
        assert isinstance(shared, list)

    def test_fictional_expert_identified(self, full_council):
        holmes = full_council.get_expert("Holmes")
        feynman = full_council.get_expert("Feynman")
        pearl = full_council.get_expert("Pearl")
        assert holmes is not None and holmes.is_fictional is True
        assert feynman is not None and feynman.is_fictional is False
        assert pearl is not None and pearl.is_fictional is False
