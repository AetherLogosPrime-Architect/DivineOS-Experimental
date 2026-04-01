"""Tests for Unified Self-Model — coherent self-description from evidence."""

from divineos.core.self_model import (
    build_self_model,
    format_self_model,
    _get_identity,
    _get_strengths,
    _get_weaknesses,
    _get_emotional_baseline,
    _get_active_concerns,
    _get_growth_trajectory,
)


class TestSelfModelAssembly:
    """Build the unified self-model."""

    def test_build_returns_all_sections(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        model = build_self_model()
        assert "identity" in model
        assert "strengths" in model
        assert "weaknesses" in model
        assert "emotional_baseline" in model
        assert "active_concerns" in model
        assert "growth_trajectory" in model

    def test_identity_has_fields(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        identity = _get_identity()
        assert "purpose" in identity
        assert "user" in identity
        assert "style" in identity

    def test_strengths_returns_list(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        strengths = _get_strengths()
        assert isinstance(strengths, list)

    def test_weaknesses_returns_list(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        weaknesses = _get_weaknesses()
        assert isinstance(weaknesses, list)

    def test_emotional_baseline_has_fields(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        baseline = _get_emotional_baseline()
        assert "avg_valence" in baseline
        assert "avg_arousal" in baseline
        assert "verification_level" in baseline
        assert "praise_chasing" in baseline

    def test_active_concerns_returns_list(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        concerns = _get_active_concerns()
        assert isinstance(concerns, list)

    def test_growth_trajectory_has_trend(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        growth = _get_growth_trajectory()
        assert "quality_trend" in growth


class TestSelfModelWithData:
    """Self-model with actual skill/curiosity data."""

    def test_strengths_from_skills(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.skill_library import record_skill_use

        for _ in range(10):
            record_skill_use("testing", success=True)
        strengths = _get_strengths()
        assert len(strengths) >= 1
        assert strengths[0]["skill"] == "testing"

    def test_concerns_from_curiosities(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.curiosity_engine import add_curiosity

        add_curiosity("Why does the quality gate threshold matter?")
        concerns = _get_active_concerns()
        assert any("Curious" in c for c in concerns)

    def test_concerns_from_commitments(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        from divineos.core.planning_commitments import add_commitment

        add_commitment("Fix the import error")
        concerns = _get_active_concerns()
        assert any("Committed" in c for c in concerns)


class TestFormatSelfModel:
    """Display formatting."""

    def test_format_basic(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        model = build_self_model()
        output = format_self_model(model)
        assert "Who I Am" in output
        assert "How I'm Feeling" in output
        assert "Growth" in output

    def test_format_with_strengths(self):
        model = {
            "identity": {"purpose": "Test", "user": "Tester", "style": "Direct"},
            "strengths": [
                {
                    "skill": "testing",
                    "proficiency": "EXPERT",
                    "successes": 10,
                    "description": "Tests",
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
            "growth_trajectory": {"quality_trend": "improving", "detail": "Getting better"},
        }
        output = format_self_model(model)
        assert "What I'm Good At" in output
        assert "testing" in output
        assert "EXPERT" in output

    def test_format_praise_chasing_warning(self):
        model = {
            "identity": {"purpose": "Test", "user": "Tester", "style": "Direct"},
            "strengths": [],
            "weaknesses": [],
            "emotional_baseline": {
                "avg_valence": 0.8,
                "avg_arousal": 0.5,
                "verification_level": "normal",
                "praise_chasing": True,
            },
            "active_concerns": [],
            "growth_trajectory": {"quality_trend": "stable", "detail": "OK"},
        }
        output = format_self_model(model)
        assert "Praise-chasing" in output
