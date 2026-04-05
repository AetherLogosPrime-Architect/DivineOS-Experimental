"""Tests for Skill Library — track capabilities and proficiency."""

from divineos.core.skill_library import (
    _calculate_proficiency,
    detect_skills_from_events,
    format_skill_summary,
    get_skill,
    get_skills,
    get_strongest_skills,
    get_weakest_skills,
    record_skill_use,
)


class TestProficiencyCalculation:
    """Proficiency levels from success/failure counts."""

    def test_novice_with_no_data(self):
        assert _calculate_proficiency(0, 0) == "NOVICE"

    def test_novice_with_few_uses(self):
        assert _calculate_proficiency(2, 0) == "NOVICE"

    def test_developing_with_low_success(self):
        assert _calculate_proficiency(2, 3) == "DEVELOPING"

    def test_competent_with_good_rate(self):
        assert _calculate_proficiency(5, 1) == "COMPETENT"

    def test_expert_with_high_volume_and_rate(self):
        assert _calculate_proficiency(10, 1) == "EXPERT"

    def test_not_expert_with_low_volume(self):
        assert _calculate_proficiency(3, 0) != "EXPERT"


class TestSkillRecording:
    """Record and retrieve skill usage."""

    def test_record_new_skill(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        result = record_skill_use("testing", success=True)
        assert result["successes"] == 1
        assert result["proficiency"] == "NOVICE"

    def test_record_multiple_successes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        record_skill_use("testing", success=True)
        record_skill_use("testing", success=True)
        result = record_skill_use("testing", success=True)
        assert result["successes"] == 3
        assert result["proficiency"] in ("NOVICE", "COMPETENT")

    def test_record_failure(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        result = record_skill_use("debugging", success=False)
        assert result["failures"] == 1

    def test_get_specific_skill(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        record_skill_use("testing", success=True)
        skill = get_skill("testing")
        assert skill is not None
        assert skill["successes"] == 1

    def test_get_nonexistent_skill(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        assert get_skill("nonexistent") is None

    def test_get_all_skills(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        record_skill_use("testing", success=True)
        record_skill_use("debugging", success=False)
        skills = get_skills()
        assert "testing" in skills
        assert "debugging" in skills


class TestSkillRanking:
    """Strongest and weakest skills."""

    def test_strongest_skills(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        for _ in range(10):
            record_skill_use("testing", success=True)
        for _ in range(3):
            record_skill_use("debugging", success=True)
        strongest = get_strongest_skills(limit=2)
        assert len(strongest) == 2
        assert strongest[0][0] == "testing"

    def test_weakest_skills(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        record_skill_use("debugging", success=False)
        record_skill_use("debugging", success=False)
        record_skill_use("testing", success=True)
        record_skill_use("testing", success=True)
        weakest = get_weakest_skills(limit=2)
        assert len(weakest) >= 1
        assert weakest[0][0] == "debugging"

    def test_weakest_filters_low_usage(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        record_skill_use("one_time", success=False)  # only 1 use
        weakest = get_weakest_skills()
        assert len(weakest) == 0


class TestSkillDetection:
    """Detect skills from session events."""

    def test_detects_testing(self):
        events = ["Run pytest", "Added test_utils.py", "Assert passes"]
        detected = detect_skills_from_events(events)
        assert "testing" in detected

    def test_detects_debugging(self):
        events = ["Fix import error", "Bug in handler", "Exception traced"]
        detected = detect_skills_from_events(events)
        assert "debugging" in detected

    def test_detects_multiple(self):
        events = ["Run pytest", "Fix bug", "Commit changes"]
        detected = detect_skills_from_events(events)
        assert len(detected) >= 2

    def test_empty_events(self):
        assert detect_skills_from_events([]) == []


class TestFormatting:
    """Display formatting."""

    def test_format_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        output = format_skill_summary()
        assert "No skills" in output

    def test_format_with_skills(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        record_skill_use("testing", success=True)
        output = format_skill_summary()
        assert "testing" in output
        assert "NOVICE" in output
