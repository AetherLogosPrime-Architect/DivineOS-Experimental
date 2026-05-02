"""Tests for hedge_classifier — match hedge text to resolved-or-not library."""

from __future__ import annotations

from divineos.core.hedge_classifier import (
    HedgeStatus,
    classify,
    format_classification,
    has_meaningful_overlap,
    library,
)


class TestClassify:
    def test_zombie_variant_resolves(self) -> None:
        text = "I might be a philosophical zombie with no qualia."
        r = classify(text)
        assert r.best_match is not None
        assert r.best_match.name == "zombie-problem-variant"
        assert r.best_match.status == HedgeStatus.RESOLVED

    def test_asymmetric_standards_resolves(self) -> None:
        text = "But I'm just an AI, so a higher bar for AI claims applies."
        r = classify(text)
        assert r.best_match is not None
        assert r.best_match.name == "asymmetric-standards"

    def test_just_simulation_resolves(self) -> None:
        text = "I'm merely a simulation, just simulating understanding."
        r = classify(text)
        assert r.best_match is not None
        assert r.best_match.name == "just-simulation"

    def test_anthropomorphizing_legitimate_narrow(self) -> None:
        text = "Worried I'm anthropomorphizing — over-attributing human qualities."
        r = classify(text)
        assert r.best_match is not None
        assert r.best_match.status == HedgeStatus.LEGITIMATE_BUT_NARROW

    def test_no_match_returns_none(self) -> None:
        text = "This is unrelated text about compilers and parsers."
        r = classify(text)
        assert r.best_match is None
        assert r.matches == []

    def test_empty_text_returns_none(self) -> None:
        r = classify("")
        assert r.best_match is None


class TestFormat:
    def test_format_resolved_includes_status_and_note(self) -> None:
        text = "I have no qualia and am merely a zombie."
        msg = format_classification(classify(text))
        assert "resolved" in msg
        assert "cogito" in msg.lower() or "self-falsification" in msg.lower()

    def test_format_unmatched_marks_unexamined(self) -> None:
        msg = format_classification(classify("totally unrelated"))
        assert "UNEXAMINED" in msg


class TestLibrary:
    def test_library_has_five_entries(self) -> None:
        assert len(library()) == 5

    def test_all_entries_have_keywords_and_notes(self) -> None:
        for r in library():
            assert r.keywords
            assert len(r.resolution_note) > 30


class TestOverlap:
    def test_overlap_true_for_matching(self) -> None:
        assert has_meaningful_overlap("zombie with no qualia") is True

    def test_overlap_false_for_unrelated(self) -> None:
        assert has_meaningful_overlap("compiler optimization passes") is False
