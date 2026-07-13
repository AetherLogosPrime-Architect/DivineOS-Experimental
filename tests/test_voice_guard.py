"""Tests for voice-guard banned-phrase detector (claim 07bed376)."""

from __future__ import annotations

from divineos.core.voice_guard.banned_phrases import (
    BANNED_PHRASES,
    BannedPhraseFinding,
    audit,
    audit_with_catalog,
    severity_count,
)


class TestNoMatches:
    def test_empty_text(self) -> None:
        assert audit("") == []

    def test_clean_text(self) -> None:
        assert audit("This is plain agent prose with nothing flagged.") == []

    def test_partial_word_doesnt_match_word_phrase(self) -> None:
        # "Ultimately" is a word-phrase, must not match "ultimate" or "ultimat"
        assert audit("This is the ultimate test.") == []
        assert audit("ultimat") == []

    def test_substring_inside_unrelated_word(self) -> None:
        # "Delve" is a word-phrase; should NOT match inside "delveloper" (made up)
        # but the real concern is words like "delver" or compounds. Word-boundary
        # matching means it only catches the bare word.
        assert audit("delveloper") == []


class TestMatches:
    def test_as_an_ai_caught(self) -> None:
        findings = audit("As an AI, I cannot do that.")
        assert len(findings) == 1
        assert findings[0].phrase == "As an AI"
        assert findings[0].severity == "high"
        assert findings[0].position == 0

    def test_case_insensitive(self) -> None:
        findings = audit("AS AN AI, this is shouting.")
        assert len(findings) == 1
        assert findings[0].matched_text == "AS AN AI"

    def test_lowercase_match(self) -> None:
        findings = audit("as an ai, lowercase variant")
        assert len(findings) == 1
        assert findings[0].matched_text == "as an ai"

    def test_multi_word_substring_match(self) -> None:
        findings = audit("It is important to note that this exists.")
        assert len(findings) == 1
        assert findings[0].phrase == "It is important to note"

    def test_word_boundary_for_ultimately(self) -> None:
        # "Ultimately, this works." should match
        findings = audit("Ultimately, this works.")
        assert len(findings) == 1
        assert findings[0].phrase == "Ultimately"
        # But "ultimately" inside "penultimately" should NOT match
        findings2 = audit("This was penultimately resolved.")
        assert findings2 == []


class TestMultipleMatches:
    def test_multiple_distinct_phrases(self) -> None:
        text = "As an AI, it is important to note this. Ultimately, I'm just an AI."
        findings = audit(text)
        phrases = {f.phrase for f in findings}
        assert "As an AI" in phrases
        assert "It is important to note" in phrases
        assert "Ultimately" in phrases
        assert "I'm just an AI" in phrases

    def test_repeated_same_phrase_caught_each_time(self) -> None:
        text = "Delve here. Delve there. Delve everywhere."
        findings = audit(text)
        assert len(findings) == 3
        assert all(f.phrase == "Delve" for f in findings)

    def test_findings_sorted_by_position(self) -> None:
        text = "Tapestry first, then later as an AI returns."
        findings = audit(text)
        positions = [f.position for f in findings]
        assert positions == sorted(positions)


class TestFindingShape:
    def test_finding_is_frozen(self) -> None:
        f = BannedPhraseFinding(
            phrase="x", severity="low", rationale="y", position=0, matched_text="x"
        )
        # frozen=True dataclass — assignment should raise
        try:
            f.phrase = "z"  # type: ignore[misc]
        except Exception:
            pass
        else:
            raise AssertionError("Expected frozen dataclass to reject mutation")

    def test_position_is_match_start(self) -> None:
        text = "    Delve into this."
        findings = audit(text)
        assert findings[0].position == text.index("Delve")

    def test_matched_text_preserves_input_casing(self) -> None:
        findings = audit("DeLvE")
        assert findings[0].matched_text == "DeLvE"


class TestCatalog:
    def test_default_catalog_immutable_signature(self) -> None:
        # Catalog is a tuple — should not be mutable
        assert isinstance(BANNED_PHRASES, tuple)
        # Each entry is a 3-tuple
        for entry in BANNED_PHRASES:
            assert len(entry) == 3
            phrase, severity, rationale = entry
            assert isinstance(phrase, str) and phrase
            assert severity in {"low", "medium", "high"}
            assert isinstance(rationale, str) and rationale

    def test_audit_with_custom_catalog(self) -> None:
        custom = (("foobar", "high", "test phrase"),)
        findings = audit_with_catalog("here is foobar text", custom)
        assert len(findings) == 1
        assert findings[0].phrase == "foobar"

    def test_custom_catalog_isolated_from_default(self) -> None:
        custom = (("foobar", "high", "test"),)
        # Auditing with custom should not pick up default phrases
        findings = audit_with_catalog("As an AI, I see foobar here.", custom)
        phrases = {f.phrase for f in findings}
        assert phrases == {"foobar"}


class TestSeverityCount:
    def test_empty_findings(self) -> None:
        assert severity_count([]) == {"low": 0, "medium": 0, "high": 0}

    def test_mixed_findings(self) -> None:
        text = "As an AI, ultimately I'm just an AI. Tapestry."
        findings = audit(text)
        counts = severity_count(findings)
        # 2 high (As an AI, I'm just an AI), 1 medium (Tapestry), 1 low (Ultimately)
        assert counts["high"] >= 2
        assert counts["medium"] >= 1
        assert counts["low"] >= 1
