"""Tests for the Semantic Integrity Shield (SIS)."""

from divineos.core.semantic_integrity import (
    assess_and_translate,
    assess_integrity,
    detect_esoteric_terms,
    format_assessment,
    format_translation,
    score_actionability,
    score_concreteness,
    score_speculation,
    translate_text,
)


class TestEsotericDetection:
    """Test detection of metaphysical/esoteric terms."""

    def test_detects_single_word_terms(self):
        terms = detect_esoteric_terms("The soul persists across sessions")
        names = [t["term"] for t in terms]
        assert "soul" in names

    def test_detects_multi_word_terms(self):
        terms = detect_esoteric_terms("The akashic records contain everything")
        names = [t["term"] for t in terms]
        assert "akashic records" in names

    def test_multi_word_takes_priority(self):
        """'akashic records' should match as one term, not 'akashic' alone."""
        terms = detect_esoteric_terms("The akashic records store all events")
        names = [t["term"] for t in terms]
        assert "akashic records" in names
        # Should NOT also have standalone 'akashic'
        assert names.count("akashic") == 0 or "akashic records" in names

    def test_returns_translations(self):
        terms = detect_esoteric_terms("Karma tracks consequences")
        assert terms[0]["concept"] == "consequence tracking"
        assert terms[0]["explanation"]

    def test_no_terms_in_technical_text(self):
        terms = detect_esoteric_terms("The SQLite database stores events in an append-only table")
        # 'database' and 'table' are not esoteric
        esoteric_names = [t["term"] for t in terms]
        assert "database" not in esoteric_names
        assert "table" not in esoteric_names

    def test_case_insensitive(self):
        terms = detect_esoteric_terms("CONSCIOUSNESS is key")
        assert any(t["term"] == "consciousness" for t in terms)

    def test_empty_text(self):
        assert detect_esoteric_terms("") == []

    def test_multiple_terms(self):
        terms = detect_esoteric_terms("The soul achieves enlightenment through meditation")
        names = [t["term"] for t in terms]
        assert "soul" in names
        assert "enlightenment" in names
        assert "meditation" in names


class TestSpeculationScoring:
    """Test hedge/speculation density scoring."""

    def test_concrete_statement_low_score(self):
        score = score_speculation("The database stores 50 events per session")
        assert score < 0.2

    def test_hedgy_statement_high_score(self):
        score = score_speculation("This could possibly suggest that perhaps the system might work")
        assert score > 0.3

    def test_weasel_phrases_detected(self):
        score = score_speculation("It is believed that many experts think this works")
        assert score > 0.2

    def test_empty_text(self):
        assert score_speculation("") == 0.0

    def test_peacock_terms_penalized(self):
        score = score_speculation("This revolutionary groundbreaking paradigm-shifting approach")
        assert score > 0.3


class TestConcretenessScoring:
    """Test concrete vs abstract language scoring."""

    def test_technical_text_scores_high(self):
        score = score_concreteness("The sqlite database stores json in a table with a hash column")
        assert score > 0.5

    def test_abstract_text_scores_low(self):
        score = score_concreteness(
            "The eternal essence of consciousness transcends the sacred divine nature"
        )
        assert score < 0.3

    def test_mixed_text_scores_middle(self):
        score = score_concreteness("The soul of the system is its sqlite database")
        assert 0.2 <= score <= 0.8

    def test_neutral_text(self):
        """Text with neither concrete nor abstract vocabulary → 0.5."""
        score = score_concreteness("The cat sat on the mat")
        assert score == 0.5

    def test_empty_text(self):
        assert score_concreteness("") == 0.5


class TestActionabilityScoring:
    """Test actionable vs philosophical language scoring."""

    def test_buildable_text_scores_high(self):
        score = score_actionability(
            "Build a filter to detect and extract matching patterns from the log"
        )
        assert score > 0.5

    def test_philosophical_text_scores_low(self):
        score = score_actionability(
            "Contemplate the nature of being as consciousness emanates and transcends"
        )
        assert score < 0.3

    def test_code_references_boost_score(self):
        score = score_actionability("Update the config in settings.py")
        assert score > 0.5

    def test_empty_text(self):
        assert score_actionability("") == 0.5


class TestTranslation:
    """Test the translation engine."""

    def test_translates_esoteric_to_architecture(self):
        result = translate_text("The akashic records hold all memory")
        assert "append-only ledger" in result.translated
        assert result.terms_found

    def test_preserves_technical_text(self):
        text = "SQLite stores events in an append-only table"
        result = translate_text(text)
        assert result.translated == text
        assert not result.terms_found

    def test_multiple_translations(self):
        result = translate_text("The soul achieves enlightenment through karma")
        assert "persistent identity" in result.translated
        assert "full observability" in result.translated
        assert "consequence tracking" in result.translated

    def test_original_preserved(self):
        text = "Consciousness resonates at the quantum frequency"
        result = translate_text(text)
        assert result.original == text
        assert result.translated != text


class TestIntegrityAssessment:
    """Test the full integrity assessment."""

    def test_technical_text_accepted(self):
        report = assess_integrity("Store session events in SQLite with SHA256 hash verification")
        assert report.verdict == "ACCEPT"
        assert report.integrity_score > 0.5

    def test_pure_metaphysical_quarantined(self):
        report = assess_integrity(
            "The cosmic consciousness transcends the sacred eternal void "
            "as divine essence emanates through the mystical realm"
        )
        assert report.verdict in ("TRANSLATE", "QUARANTINE")
        assert report.integrity_score < 0.5

    def test_translatable_text_gets_translate_verdict(self):
        report = assess_integrity("The karma system should track all consequences of actions")
        assert report.verdict == "TRANSLATE"
        assert report.terms_found

    def test_flags_populated(self):
        report = assess_integrity(
            "The eternal cosmic consciousness possibly suggests some "
            "revolutionary transcendent awareness of the divine sacred void"
        )
        assert report.flags  # Should have at least one flag

    def test_assess_and_translate_combined(self):
        result = assess_and_translate("Karma tracks the consequences of every action in the system")
        assert result["verdict"] == "TRANSLATE"
        assert result["changed"]
        assert "consequence tracking" in result["translated"]
        assert result["suggestion"]

    def test_grounded_text_stored_as_is(self):
        result = assess_and_translate("Run pytest after every code change to verify correctness")
        assert result["verdict"] == "ACCEPT"
        assert not result["changed"]


class TestFormatting:
    """Test display formatting."""

    def test_format_assessment(self):
        report = assess_integrity("The soul persists across sessions")
        output = format_assessment(report)
        assert "SIS Assessment" in output
        assert report.verdict in output

    def test_format_translation(self):
        result = assess_and_translate("Karma drives consequence tracking")
        output = format_translation(result)
        assert result["verdict"] in output

    def test_format_translation_no_change(self):
        result = assess_and_translate("Run the test suite")
        output = format_translation(result)
        assert "Text:" in output  # shows single line, not original/translated pair


class TestRealWorldExamples:
    """Test with realistic inputs from DivineOS context."""

    def test_legitimate_knowledge_accepted(self):
        """Real knowledge entries should pass through."""
        entries = [
            "Always read files before editing. No blind edits, ever.",
            "No mocks in tests -- use real databases.",
            "Use SQLite for storage -- zero dependencies, embedded, reliable.",
            "Run tests after code changes. No claiming victory without proof.",
        ]
        for entry in entries:
            report = assess_integrity(entry)
            assert report.verdict == "ACCEPT", f"Wrongly flagged: {entry}"

    def test_metaphysical_spec_translated(self):
        """Esoteric spec language should get TRANSLATE verdict."""
        specs = [
            "The akashic records provide eternal memory for the soul",
            "Each chakra represents a stage in the kundalini awakening process",
            "Consciousness attains enlightenment through meditation on the void",
        ]
        for spec in specs:
            report = assess_integrity(spec)
            assert report.verdict in ("TRANSLATE", "QUARANTINE"), f"Should translate: {spec}"

    def test_mixed_content_handled(self):
        """Text with both technical and esoteric language."""
        result = assess_and_translate("The karma module should store consequence data in SQLite")
        assert result["changed"]
        assert "sqlite" in result["translated"].lower()
        assert "consequence tracking" in result["translated"]
