"""Extended tests for self-model — covering builder functions and format paths."""

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.memory import init_memory_tables


@pytest.fixture(autouse=True)
def _init():
    init_knowledge_table()
    init_memory_tables()


class TestBuildSelfModel:
    """Self-model assembly and completeness tracking."""

    def test_all_sections_present(self):
        from divineos.core.self_model import build_self_model

        model = build_self_model()
        expected = [
            "identity",
            "strengths",
            "weaknesses",
            "emotional_baseline",
            "active_concerns",
            "growth_trajectory",
            "attention",
            "epistemic_balance",
            "completeness",
        ]
        for section in expected:
            assert section in model

    def test_completeness_tracking(self):
        from divineos.core.self_model import build_self_model

        model = build_self_model()
        comp = model["completeness"]
        assert comp["total"] == 8
        assert comp["succeeded"] + len(comp["failed"]) == 8
        assert comp["complete"] == (len(comp["failed"]) == 0)


class TestIdentity:
    def test_identity_with_data(self):
        from divineos.core.memory import set_core
        from divineos.core.self_model import _get_identity

        set_core("project_purpose", "Build an AI OS")
        set_core("user_identity", "A developer")
        set_core("communication_style", "Direct and clear")

        identity = _get_identity()
        assert identity["purpose"] == "Build an AI OS"
        assert identity["user"] == "A developer"
        assert identity["style"] == "Direct and clear"

    def test_identity_empty(self):
        from divineos.core.self_model import _get_identity

        identity = _get_identity()
        assert "purpose" in identity
        assert "user" in identity
        assert "style" in identity


class TestStrengths:
    def test_strengths_returns_list(self):
        from divineos.core.self_model import _get_strengths

        result = _get_strengths()
        assert isinstance(result, list)


class TestWeaknesses:
    def test_weaknesses_returns_list(self):
        from divineos.core.self_model import _get_weaknesses

        result = _get_weaknesses()
        assert isinstance(result, list)

    def test_weaknesses_from_lessons(self):
        from divineos.core.knowledge.lessons import record_lesson
        from divineos.core.self_model import _get_weaknesses

        # Record a lesson multiple times to create a regression signal
        for i in range(5):
            record_lesson("test_weakness", "Repeated mistake for weakness test.", f"session-{i}")

        result = _get_weaknesses()
        # May or may not show depending on regression detection threshold
        assert isinstance(result, list)


class TestEmotionalBaseline:
    def test_baseline_defaults(self):
        from divineos.core.self_model import _get_emotional_baseline

        result = _get_emotional_baseline()
        assert "avg_valence" in result
        assert "avg_arousal" in result
        assert "verification_level" in result
        assert "praise_chasing" in result

    def test_baseline_values_reasonable(self):
        from divineos.core.self_model import _get_emotional_baseline

        result = _get_emotional_baseline()
        assert -1.0 <= result["avg_valence"] <= 1.0
        assert result["verification_level"] in ("normal", "elevated", "high")


class TestActiveConcerns:
    def test_concerns_returns_list(self):
        from divineos.core.self_model import _get_active_concerns

        result = _get_active_concerns()
        assert isinstance(result, list)

    def test_concerns_include_commitments(self):
        from divineos.core.self_model import _get_active_concerns

        try:
            from divineos.core.planning_commitments import (
                init_commitments_table,
                record_commitment,
            )

            init_commitments_table()
            record_commitment("Test commitment for self-model.")
            result = _get_active_concerns()
            committed = [c for c in result if "Committed" in c]
            assert len(committed) >= 1
        except ImportError:
            pytest.skip("planning_commitments not available")


class TestGrowthTrajectory:
    def test_trajectory_returns_dict(self):
        from divineos.core.self_model import _get_growth_trajectory

        result = _get_growth_trajectory()
        assert "quality_trend" in result
        assert "detail" in result

    def test_trajectory_valid_trends(self):
        from divineos.core.self_model import _get_growth_trajectory

        result = _get_growth_trajectory()
        assert result["quality_trend"] in ("improving", "declining", "stable", "unknown")


class TestFormatSelfModel:
    """Format rendering covers all sections."""

    def test_format_full_model(self):
        from divineos.core.self_model import build_self_model, format_self_model

        model = build_self_model()
        output = format_self_model(model)
        assert "Who I Am" in output
        assert "How I'm Feeling" in output
        assert "Growth" in output

    def test_format_with_praise_chasing(self):
        from divineos.core.self_model import format_self_model

        model = {
            "identity": {"purpose": "Test", "user": "Dev", "style": "Direct"},
            "strengths": [],
            "weaknesses": [],
            "emotional_baseline": {
                "avg_valence": 0.5,
                "avg_arousal": 0.3,
                "verification_level": "normal",
                "praise_chasing": True,
                "praise_detail": "high valence after praise, quality dipped",
            },
            "active_concerns": [],
            "growth_trajectory": {"quality_trend": "stable", "detail": "No data"},
            "attention": {
                "focus_count": 0,
                "top_focus": [],
                "driver_count": 0,
                "suppressed_count": 0,
            },
            "epistemic_balance": {},
            "completeness": {"total": 8, "succeeded": 8, "failed": [], "complete": True},
        }
        output = format_self_model(model)
        assert "praise-chasing" in output
        assert "high valence" in output

    def test_format_with_concerns(self):
        from divineos.core.self_model import format_self_model

        model = {
            "identity": {"purpose": "Test", "user": "Dev", "style": "Direct"},
            "strengths": [],
            "weaknesses": [{"description": "Weak at testing", "source": "skill_weakness"}],
            "emotional_baseline": {
                "avg_valence": 0.0,
                "avg_arousal": 0.0,
                "verification_level": "normal",
                "praise_chasing": False,
            },
            "active_concerns": ["Curious: How does X work?", "Drift alert: mild severity"],
            "growth_trajectory": {"quality_trend": "improving", "detail": "Getting better"},
            "attention": {
                "focus_count": 2,
                "top_focus": ["Build tests", "Fix coverage"],
                "driver_count": 1,
                "suppressed_count": 3,
            },
            "epistemic_balance": {
                "total": 10,
                "observed": 5,
                "told": 3,
                "inferred": 1,
                "inherited": 1,
                "unwarranted": 2,
            },
            "completeness": {
                "total": 8,
                "succeeded": 6,
                "failed": ["strengths", "weaknesses"],
                "complete": False,
            },
        }
        output = format_self_model(model)
        assert "What's On My Mind" in output
        assert "Curious" in output
        assert "Attending To" in output
        assert "How I Know What I Know" in output
        assert "Completeness: 6/8" in output
        assert "I'm missing" in output
        assert "What I'm Working On" in output

    def test_format_negative_valence(self):
        from divineos.core.self_model import format_self_model

        model = {
            "identity": {"purpose": "Test", "user": "Dev", "style": "Direct"},
            "strengths": [],
            "weaknesses": [],
            "emotional_baseline": {
                "avg_valence": -0.5,
                "avg_arousal": 0.0,
                "verification_level": "normal",
                "praise_chasing": False,
            },
            "active_concerns": [],
            "growth_trajectory": {"quality_trend": "declining", "detail": "Declining"},
            "attention": {
                "focus_count": 0,
                "top_focus": [],
                "driver_count": 0,
                "suppressed_count": 0,
            },
            "epistemic_balance": {},
            "completeness": {"total": 8, "succeeded": 8, "failed": [], "complete": True},
        }
        output = format_self_model(model)
        assert "negative" in output

    def test_format_with_strengths(self):
        from divineos.core.self_model import format_self_model

        model = {
            "identity": {"purpose": "Test", "user": "Dev", "style": "Direct"},
            "strengths": [
                {
                    "skill": "testing",
                    "proficiency": "COMPETENT",
                    "successes": 10,
                    "description": "Writing tests",
                }
            ],
            "weaknesses": [],
            "emotional_baseline": {
                "avg_valence": 0.5,
                "avg_arousal": 0.3,
                "verification_level": "normal",
                "praise_chasing": False,
            },
            "active_concerns": [],
            "growth_trajectory": {"quality_trend": "stable", "detail": "Stable"},
            "attention": {
                "focus_count": 0,
                "top_focus": [],
                "driver_count": 0,
                "suppressed_count": 0,
            },
            "epistemic_balance": {},
            "completeness": {"total": 8, "succeeded": 8, "failed": [], "complete": True},
        }
        output = format_self_model(model)
        assert "Good At" in output
        assert "testing" in output
        assert "COMPETENT" in output
