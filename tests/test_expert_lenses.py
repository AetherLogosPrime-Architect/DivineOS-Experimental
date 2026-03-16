"""Tests for the expert lenses system."""

import pytest
from divineos.expert_lenses import (
    get_expert,
    list_experts,
    route,
    generate_framework_prompt,
)


class TestExpertLens:
    def test_dataclass_fields(self):
        expert = get_expert("feynman")
        assert expert.name == "feynman"
        assert expert.display_name == "Richard Feynman"
        assert expert.domain == "First Principles & Clarity"
        assert len(expert.framework_steps) == 5
        assert len(expert.key_questions) == 5
        assert isinstance(expert.domains, frozenset)
        assert len(expert.detects) > 0

    def test_immutable(self):
        expert = get_expert("feynman")
        with pytest.raises(AttributeError):
            expert.name = "changed"  # type: ignore[misc]


class TestListExperts:
    def test_returns_all_five(self):
        experts = list_experts()
        assert len(experts) == 5

    def test_sorted_by_name(self):
        experts = list_experts()
        names = [e.name for e in experts]
        assert names == sorted(names)

    def test_all_have_required_fields(self):
        for expert in list_experts():
            assert expert.name
            assert expert.display_name
            assert expert.domain
            assert expert.description
            assert len(expert.framework_steps) >= 3
            assert len(expert.key_questions) >= 3
            assert len(expert.domains) >= 5
            assert len(expert.detects) >= 2


class TestGetExpert:
    def test_finds_by_name(self):
        expert = get_expert("pearl")
        assert expert.display_name == "Judea Pearl"

    def test_case_insensitive(self):
        expert = get_expert("PEARL")
        assert expert.name == "pearl"

    def test_raises_for_unknown(self):
        with pytest.raises(KeyError, match="Unknown expert"):
            get_expert("nonexistent")

    def test_error_lists_available(self):
        with pytest.raises(KeyError, match="feynman"):
            get_expert("unknown")


class TestRoute:
    def test_causality_routes_to_pearl(self):
        results = route("Is this correlation or causality?")
        names = [e.name for e, _ in results]
        assert "pearl" in names

    def test_safety_routes_to_yudkowsky(self):
        results = route("Is this AI system safe and aligned?")
        names = [e.name for e, _ in results]
        assert "yudkowsky" in names

    def test_ethics_routes_to_nussbaum(self):
        results = route("What are the ethics and justice implications?")
        names = [e.name for e, _ in results]
        assert "nussbaum" in names

    def test_learning_routes_to_hinton(self):
        results = route("Is this neural network architecture right for training?")
        names = [e.name for e, _ in results]
        assert "hinton" in names

    def test_simplification_routes_to_feynman(self):
        results = route("Can we simplify this using first principles and clarity?")
        names = [e.name for e, _ in results]
        assert "feynman" in names

    def test_max_experts_respected(self):
        results = route("ethics safety learning causality", max_experts=2)
        assert len(results) <= 2

    def test_scores_are_descending(self):
        results = route("ethics fairness justice human rights impact policy")
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_scores_between_zero_and_one(self):
        results = route("anything about safety and ethics")
        for _, score in results:
            assert 0.0 < score <= 1.0


class TestRouteNoMatch:
    def test_fallback_to_feynman(self):
        results = route("xyzzy blorp fnord")
        assert len(results) == 1
        assert results[0][0].name == "feynman"
        assert results[0][1] == 0.1


class TestGenerateFrameworkPrompt:
    def test_includes_expert_name(self):
        expert = get_expert("feynman")
        prompt = generate_framework_prompt(expert, "Why is the sky blue?")
        assert "Richard Feynman" in prompt

    def test_includes_question(self):
        expert = get_expert("pearl")
        prompt = generate_framework_prompt(expert, "Does coffee cause productivity?")
        assert "Does coffee cause productivity?" in prompt

    def test_includes_all_steps(self):
        expert = get_expert("yudkowsky")
        prompt = generate_framework_prompt(expert, "Is this AI safe?")
        for i in range(1, len(expert.framework_steps) + 1):
            assert f"### Step {i}" in prompt

    def test_includes_key_questions(self):
        expert = get_expert("nussbaum")
        prompt = generate_framework_prompt(expert, "Is this policy fair?")
        assert "Key Questions" in prompt
        for q in expert.key_questions:
            assert q in prompt

    def test_includes_detects(self):
        expert = get_expert("hinton")
        prompt = generate_framework_prompt(expert, "Will this network learn?")
        assert "What This Lens Detects" in prompt

    def test_output_is_markdown(self):
        expert = get_expert("feynman")
        prompt = generate_framework_prompt(expert, "test question")
        assert prompt.startswith("## ")
        assert "###" in prompt
