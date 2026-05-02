"""Tests for the value-tension detector."""

from divineos.core.value_tensions import (
    TensionPattern,
    TensionReport,
    _cluster_tensions,
    _normalize_tension,
    _tension_similarity,
    detect_tension_patterns,
    format_tension_summary,
)


class TestNormalize:
    def test_lowercases(self):
        assert _normalize_tension("Speed vs Safety") == "speed vs safety"

    def test_strips_whitespace(self):
        assert _normalize_tension("  speed  vs  safety  ") == "speed vs safety"

    def test_strips_trailing_punctuation(self):
        assert _normalize_tension("speed vs safety.") == "speed vs safety"
        assert _normalize_tension("speed vs safety!") == "speed vs safety"

    def test_empty(self):
        assert _normalize_tension("") == ""


class TestSimilarity:
    def test_identical(self):
        assert _tension_similarity("speed vs safety", "speed vs safety") == 1.0

    def test_high_overlap(self):
        score = _tension_similarity("speed vs safety", "safety vs speed")
        assert score > 0.8

    def test_no_overlap(self):
        assert _tension_similarity("apples oranges", "cats dogs") == 0.0

    def test_empty(self):
        assert _tension_similarity("", "something") == 0.0
        assert _tension_similarity("something", "") == 0.0


class TestClustering:
    def test_empty_input(self):
        assert _cluster_tensions([]) == []

    def test_single_tension(self):
        tensions = [{"tension": "speed vs safety", "decision_id": "a", "content": "chose speed"}]
        patterns = _cluster_tensions(tensions)
        assert len(patterns) == 1
        assert patterns[0].occurrences == 1

    def test_groups_similar(self):
        tensions = [
            {"tension": "speed vs safety", "decision_id": "a", "content": "chose speed"},
            {"tension": "safety vs speed", "decision_id": "b", "content": "chose safety"},
            {"tension": "thoroughness vs brevity", "decision_id": "c", "content": "chose brief"},
        ]
        patterns = _cluster_tensions(tensions)
        # speed/safety should cluster, thoroughness/brevity separate
        assert len(patterns) == 2
        speed_safety = [p for p in patterns if "speed" in p.tension_text]
        assert len(speed_safety) == 1
        assert speed_safety[0].occurrences == 2

    def test_sorted_by_frequency(self):
        tensions = [
            {"tension": "x vs y", "decision_id": "1", "content": "a"},
            {"tension": "a vs b", "decision_id": "2", "content": "b"},
            {"tension": "a vs b", "decision_id": "3", "content": "c"},
            {"tension": "a vs b", "decision_id": "4", "content": "d"},
        ]
        patterns = _cluster_tensions(tensions)
        assert patterns[0].occurrences >= patterns[-1].occurrences


class TestFormatSummary:
    def test_empty_report(self):
        report = TensionReport(patterns=[], total_decisions_with_tension=0, total_decisions=5)
        assert format_tension_summary(report) == ""

    def test_formats_patterns(self):
        report = TensionReport(
            patterns=[
                TensionPattern(
                    tension_text="speed vs safety",
                    occurrences=3,
                    decision_ids=["a", "b", "c"],
                    resolutions=["chose speed", "chose safety", "balanced"],
                ),
            ],
            total_decisions_with_tension=3,
            total_decisions=10,
        )
        text = format_tension_summary(report)
        assert "Recurring Value Tensions" in text
        assert "speed vs safety" in text
        assert "3x" in text
        assert "Last chose: chose speed" in text

    def test_frequent_gets_lightning(self):
        report = TensionReport(
            patterns=[
                TensionPattern("a vs b", 3, ["x", "y", "z"], ["r1", "r2", "r3"]),
            ],
            total_decisions_with_tension=3,
            total_decisions=5,
        )
        text = format_tension_summary(report)
        assert "⚡" in text

    def test_infrequent_gets_arrow(self):
        report = TensionReport(
            patterns=[
                TensionPattern("a vs b", 2, ["x", "y"], ["r1", "r2"]),
            ],
            total_decisions_with_tension=2,
            total_decisions=5,
        )
        text = format_tension_summary(report)
        assert "↔" in text


class TestDetectPatterns:
    def test_no_decisions(self, tmp_path, monkeypatch):
        """Works with empty decision journal."""
        report = detect_tension_patterns()
        assert report.total_decisions == 0
        assert report.patterns == []

    def test_with_tensions(self, tmp_path, monkeypatch):
        """Detects patterns from actual recorded decisions."""
        from divineos.core.decision_journal import record_decision

        # Record several decisions with similar tensions
        record_decision("chose speed", tension="speed vs thoroughness")
        record_decision("chose speed again", tension="thoroughness vs speed")
        record_decision("went careful", tension="speed vs thoroughness")
        record_decision("unrelated", tension="simplicity vs flexibility")

        report = detect_tension_patterns()
        assert report.total_decisions_with_tension == 4
        assert report.total_decisions == 4
        # The speed/thoroughness tension should cluster
        assert len(report.patterns) >= 1
