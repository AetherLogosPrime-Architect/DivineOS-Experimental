"""Tests for Curiosity Engine — track what the agent wants to learn."""

from divineos.core.curiosity_engine import (
    add_curiosity,
    add_note,
    answer_curiosity,
    detect_curiosities,
    format_curiosities,
    get_all_curiosities,
    get_open_curiosities,
    shelve_curiosity,
)


class TestCuriosityOperations:
    """Add, answer, and shelve curiosities."""

    def test_add_curiosity(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        result = add_curiosity("Why does the quality gate use 0.5 as the honesty threshold?")
        assert result["status"] == "OPEN"
        assert result["question"].startswith("Why does")

    def test_deduplicates(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_curiosity("What causes drift?")
        add_curiosity("What causes drift?")
        assert len(get_open_curiosities()) == 1

    def test_add_note(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_curiosity("Why does X happen?")
        result = add_note("Why does X happen?", "Found clue in session analyzer")
        assert result is True
        curiosities = get_open_curiosities()
        assert curiosities[0]["status"] == "INVESTIGATING"
        assert len(curiosities[0]["notes"]) == 1

    def test_answer_curiosity(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_curiosity("Why does X happen?")
        result = answer_curiosity("Why does X happen?", "Because of Y")
        assert result is True
        assert len(get_open_curiosities()) == 0
        all_c = get_all_curiosities()
        assert all_c[0]["status"] == "ANSWERED"
        assert all_c[0]["answer"] == "Because of Y"

    def test_shelve_curiosity(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_curiosity("Why does X happen?")
        result = shelve_curiosity("Why does X happen?")
        assert result is True
        assert len(get_open_curiosities()) == 0

    def test_answer_nonexistent(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        assert answer_curiosity("No such question", "answer") is False

    def test_category_stored(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        result = add_curiosity("How?", category="architecture")
        assert result["category"] == "architecture"


class TestCuriosityDetection:
    """Detect curiosity language in text."""

    def test_detects_i_wonder(self):
        result = detect_curiosities("I wonder why the tests take so long to run")
        assert len(result) == 1

    def test_detects_how_does(self):
        result = detect_curiosities("How does the maturity pipeline decide promotions")
        assert len(result) == 1

    def test_detects_what_if(self):
        result = detect_curiosities("What if we used graph edges for consolidation")
        assert len(result) == 1

    def test_detects_worth_investigating(self):
        result = detect_curiosities("This pattern is worth investigating further")
        assert len(result) == 1

    def test_ignores_non_curious(self):
        result = detect_curiosities("The test passed successfully")
        assert len(result) == 0

    def test_ignores_empty(self):
        assert detect_curiosities("") == []

    def test_ignores_short(self):
        assert detect_curiosities("why") == []


class TestFormatting:
    """Display formatting."""

    def test_format_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        output = format_curiosities()
        assert "No open" in output

    def test_format_with_curiosities(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_curiosity("Why does X happen?")
        output = format_curiosities()
        assert "1 open" in output
        assert "Why does" in output

    def test_format_with_notes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        add_curiosity("Why does X happen?")
        add_note("Why does X happen?", "Some clue")
        output = format_curiosities()
        assert "1 note" in output
