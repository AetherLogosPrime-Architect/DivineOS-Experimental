"""Tests for the knowledge-citation extractor — auto-link substrate for #74."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from divineos.core.knowledge_citation import extract_id_citations, find_cited_knowledge_ids


class TestExtractIdCitations:
    """The raw-token extractor — no store lookup, just pattern match."""

    def test_full_hex_id_extracted(self):
        text = "Per knowledge entry 9682167cabcdef1234567890abcdef12 the answer is X"
        out = extract_id_citations(text)
        assert "9682167cabcdef1234567890abcdef12" in out

    def test_8_char_prefix_extracted(self):
        text = "See 9682167c for the original observation"
        out = extract_id_citations(text)
        assert "9682167c" in out

    def test_too_short_ignored(self):
        # 7-char hex run is below the minimum; should not extract.
        text = "the value abcdef1 is too short"
        out = extract_id_citations(text)
        assert "abcdef1" not in out

    def test_multiple_ids_extracted_in_order(self):
        text = "First aaaaaaaa then bbbbbbbb later cccccccc"
        out = extract_id_citations(text)
        assert out == ["aaaaaaaa", "bbbbbbbb", "cccccccc"]

    def test_duplicate_ids_deduped(self):
        text = "abc12345 appears twice: abc12345 again"
        out = extract_id_citations(text)
        assert out.count("abc12345") == 1

    def test_non_hex_word_ignored(self):
        # Real english words that aren't hex must not match (e.g., "feedback"
        # has no a-f hex run of 8+ chars that's a separate word).
        text = "decided to provide feedback on the proposal yesterday"
        out = extract_id_citations(text)
        # No standalone hex tokens of length >= 8 in plain english
        assert out == []

    def test_case_insensitive(self):
        text = "see ABCDEF12 and abcdef34"
        out = extract_id_citations(text)
        assert "abcdef12" in out
        assert "abcdef34" in out

    def test_empty_returns_empty(self):
        assert extract_id_citations("") == []
        assert extract_id_citations(None) == []  # type: ignore[arg-type]


class TestFindCitedKnowledgeIds:
    """The store-verified extractor — only returns ids that actually exist."""

    def test_no_citations_returns_empty(self):
        out = find_cited_knowledge_ids("just plain text no ids here")
        assert out == []

    def test_full_id_exact_match(self):
        text = "Cited: 9682167cabcdef1234567890abcdef12"
        with patch("divineos.core.knowledge._base.get_connection") as gc:
            conn = MagicMock()
            cur = MagicMock()
            conn.__enter__.return_value = conn
            conn.cursor.return_value = cur
            cur.fetchone.return_value = ("9682167cabcdef1234567890abcdef12",)
            gc.return_value = conn
            out = find_cited_knowledge_ids(text)
        assert out == ["9682167cabcdef1234567890abcdef12"]

    def test_prefix_unique_match_returns_full_id(self):
        text = "See 9682167c for details"
        with patch("divineos.core.knowledge._base.get_connection") as gc:
            conn = MagicMock()
            cur = MagicMock()
            conn.__enter__.return_value = conn
            conn.cursor.return_value = cur
            cur.fetchall.return_value = [("9682167cabcdef1234567890abcdef12",)]
            gc.return_value = conn
            out = find_cited_knowledge_ids(text)
        assert out == ["9682167cabcdef1234567890abcdef12"]

    def test_prefix_ambiguous_match_drops_silently(self):
        # Two matching entries → don't guess; drop the citation.
        # Better no-link than wrong-link (per #78 letter-citation lesson).
        text = "See abcd1234 for details"
        with patch("divineos.core.knowledge._base.get_connection") as gc:
            conn = MagicMock()
            cur = MagicMock()
            conn.__enter__.return_value = conn
            conn.cursor.return_value = cur
            cur.fetchall.return_value = [
                ("abcd1234ffffffffffffffffffffffff",),
                ("abcd1234eeeeeeeeeeeeeeeeeeeeeeee",),
            ]
            gc.return_value = conn
            out = find_cited_knowledge_ids(text)
        assert out == []

    def test_store_error_fail_soft(self):
        # If the store raises, return [] rather than propagating.
        text = "Cited: deadbeef12345678"
        with patch(
            "divineos.core.knowledge._base.get_connection",
            side_effect=RuntimeError("store unavailable"),
        ):
            out = find_cited_knowledge_ids(text)
        assert out == []

    def test_unverified_citation_silently_dropped(self):
        # Citation that doesn't match any entry → dropped, not guessed.
        text = "See 12345678 for details"
        with patch("divineos.core.knowledge._base.get_connection") as gc:
            conn = MagicMock()
            cur = MagicMock()
            conn.__enter__.return_value = conn
            conn.cursor.return_value = cur
            cur.fetchall.return_value = []  # no matches
            gc.return_value = conn
            out = find_cited_knowledge_ids(text)
        assert out == []
