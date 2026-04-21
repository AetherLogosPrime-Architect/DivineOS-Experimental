"""Tests for the Dynamic Council Manager."""

import pytest

from divineos.core.council.engine import CouncilEngine
from divineos.core.council.manager import (
    ALWAYS_ON,
    CouncilManager,
    ExpertScore,
    ManagedCouncilResult,
    classify_problem,
    score_experts,
    select_experts,
)


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def full_engine():
    """Engine with all 32 experts registered."""
    from divineos.core.council import experts

    engine = CouncilEngine()
    for name in sorted(dir(experts)):
        if name.startswith("create_") and name.endswith("_wisdom"):
            fn = getattr(experts, name)
            engine.register(fn())
    return engine


@pytest.fixture
def manager(full_engine):
    return CouncilManager(full_engine)


# ── Classification Tests ────────────────────────────────────────────


class TestClassifyProblem:
    def test_causal_chain_detected(self):
        cats = classify_problem("The query returns wrong results due to a regression")
        names = [c.name for c, _ in cats]
        assert "causal_chain" in names

    def test_logic_error_detected(self):
        cats = classify_problem("off-by-one error at the boundary")
        names = [c.name for c, _ in cats]
        assert "logic_error" in names

    def test_security_detected(self):
        cats = classify_problem("SQL injection vulnerability in auth middleware")
        names = [c.name for c, _ in cats]
        assert "security" in names

    def test_format_spec_detected(self):
        cats = classify_problem("FITS header field exceeds width limit per the spec")
        names = [c.name for c, _ in cats]
        assert "format_spec" in names

    def test_multiple_categories(self):
        cats = classify_problem("Wrong result at the boundary edge case in the format output")
        names = [c.name for c, _ in cats]
        assert len(names) >= 2

    def test_no_category_on_empty(self):
        cats = classify_problem("")
        assert cats == []

    def test_sorted_by_score(self):
        cats = classify_problem(
            "security vulnerability injection auth permission untrusted malicious input"
        )
        if len(cats) >= 2:
            scores = [s for _, s in cats]
            assert scores == sorted(scores, reverse=True)


# ── Scoring Tests ───────────────────────────────────────────────────


class TestScoreExperts:
    def test_always_on_get_baseline(self, full_engine):
        scored = score_experts("some problem", full_engine.experts)
        score_map = {es.expert_name: es for es in scored}
        for name in ALWAYS_ON:
            assert score_map[name].score >= 3.0
            assert "always-on" in score_map[name].reasons

    def test_core_experts_score_high(self, full_engine):
        scored = score_experts(
            "SQL injection vulnerability in auth",
            full_engine.experts,
        )
        score_map = {es.expert_name: es for es in scored}
        assert score_map["Schneier"].score > score_map.get("Aristotle", ExpertScore("x", 0)).score

    def test_knuth_dominates_boundary_bugs(self, full_engine):
        scored = score_experts(
            "field width limit spec truncation format boundary",
            full_engine.experts,
        )
        # Knuth should be top non-always-on expert
        non_always = [es for es in scored if es.expert_name not in ALWAYS_ON]
        assert non_always[0].expert_name == "Knuth"

    def test_pearl_feynman_on_causal(self, full_engine):
        scored = score_experts(
            "wrong result regression unexpected behavior downstream",
            full_engine.experts,
        )
        top_8 = {es.expert_name for es in scored[:8]}
        assert "Pearl" in top_8
        assert "Feynman" in top_8


# ── Selection Tests ─────────────────────────────────────────────────


class TestSelectExperts:
    def test_always_on_included(self, full_engine):
        selected = select_experts("any problem", full_engine.experts)
        names = {es.expert_name for es in selected}
        for name in ALWAYS_ON:
            assert name in names

    def test_respects_min(self, full_engine):
        selected = select_experts("some problem", full_engine.experts, min_experts=5)
        assert len(selected) >= 5

    def test_respects_max(self, full_engine):
        selected = select_experts(
            "security vulnerability injection auth boundary edge case "
            "wrong result regression format width spec",
            full_engine.experts,
            max_experts=8,
        )
        assert len(selected) <= 8

    def test_focused_problem_gets_fewer_experts(self, full_engine):
        # A very focused problem should select closer to min
        focused = select_experts("FITS header field width", full_engine.experts)
        # A broad problem should select closer to max
        broad = select_experts(
            "security vulnerability with wrong results at boundary "
            "edge case after regression caused by state leak",
            full_engine.experts,
        )
        assert len(focused) <= len(broad)


# ── Manager Integration Tests ──────────────────────────────────────


class TestCouncilManager:
    def test_convene_returns_managed_result(self, manager):
        result = manager.convene("wrong query results")
        assert isinstance(result, ManagedCouncilResult)
        assert result.total_experts_available == 32
        assert len(result.analyses) <= 8
        assert len(result.analyses) >= 5

    def test_convene_includes_categories(self, manager):
        result = manager.convene("security injection vulnerability")
        assert any(name == "security" for name, _ in result.categories_detected)

    def test_force_experts(self, manager):
        result = manager.convene(
            "simple problem",
            force_experts=["Shannon", "Godel"],
        )
        names = {a.expert_name for a in result.analyses}
        assert "Shannon" in names
        assert "Godel" in names

    def test_selection_summary_is_readable(self, manager):
        result = manager.convene("wrong result at boundary")
        summary = result.selection_summary()
        assert "Selected" in summary
        assert "of 32 experts" in summary

    def test_explain_selection(self, manager):
        explanation = manager.explain_selection("SQL injection in auth middleware")
        assert "Schneier" in explanation
        assert "security" in explanation.lower()
        assert "Selected" in explanation

    def test_synthesis_comes_from_selected_only(self, manager):
        result = manager.convene("FITS header field width spec")
        analysis_names = {a.expert_name for a in result.analyses}
        # Should NOT have all 32 — selection should pick 5-8
        assert len(analysis_names) < 32
        # Should have Knuth for this problem
        assert "Knuth" in analysis_names
