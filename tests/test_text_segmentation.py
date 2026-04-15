"""Tests for text segmentation — breaking large text blocks into atomic chunks."""

from divineos.core.knowledge._text import segment_large_text


class TestSegmentLargeText:
    """Core segmentation logic."""

    def test_short_text_returns_unchanged(self):
        """Text under threshold comes back as single-element list."""
        text = "This is a short observation about knowledge storage."
        result = segment_large_text(text)
        assert result == [text]

    def test_single_paragraph_returns_unchanged(self):
        """Long text with no paragraph breaks stays as one entry."""
        text = "A " * 300  # 600 chars, above threshold, but no breaks
        result = segment_large_text(text)
        assert len(result) == 1

    def test_paragraph_split(self):
        """Double-newline separated paragraphs become separate segments."""
        para1 = "The knowledge extraction pipeline processes content in monolithic chunks. " * 3
        para2 = (
            "The FTS5 index uses implicit AND logic which kills recall on multi-term queries. " * 3
        )
        para3 = (
            "The maturity lifecycle promotes entries from RAW to HYPOTHESIS when corroborated. " * 3
        )
        text = f"{para1}\n\n{para2}\n\n{para3}"
        result = segment_large_text(text)
        assert len(result) == 3

    def test_numbered_list_split(self):
        """Numbered list items are split into separate segments."""
        text = (
            "1. The stemmed overlap function still uses min-denominator instead of "
            "Dice coefficient, which inflates similarity scores for short entries.\n"
            "2. The FTS5 query builder joins terms with implicit AND, causing recall "
            "to drop sharply when queries have more than three key terms.\n"
            "3. Seven hardcoded threshold values in the relationship classification "
            "module need extraction to constants.py for maintainability."
        )
        result = segment_large_text(text)
        assert len(result) == 3

    def test_bulleted_list_split(self):
        """Bullet-pointed items are split into separate segments."""
        text = (
            "- The knowledge maturity pipeline is stalled because entries born with "
            "corroboration_count=0 can never meet the promotion gate of >=1.\n"
            "- Lesson resolution is stuck at zero because the stimulus gate requires "
            "sessions where the lesson triggered, but low-frequency lessons never trigger.\n"
            "- The extraction pipeline stores raw pasted text as single blob entries "
            "instead of breaking them into discrete, actionable knowledge pieces."
        )
        result = segment_large_text(text)
        assert len(result) == 3

    def test_metadata_lines_filtered(self):
        """Markdown headers, separators, and metadata are stripped."""
        text = (
            "## Round 7 Findings\n"
            "=================\n\n"
            "The stemmed overlap function still uses min-denominator instead of "
            "Dice coefficient, which inflates similarity scores for short entries. "
            "This causes false dedup matches between entries that are actually "
            "discussing completely different topics in the knowledge store.\n\n"
            "Score: 8\n"
            "Date: 2026-04-10\n\n"
            "The FTS5 query builder joins terms with implicit AND logic which "
            "causes recall to drop sharply when queries contain more than three "
            "key terms. Switching to OR-joined terms would dramatically improve "
            "search recall without significantly hurting precision scores."
        )
        result = segment_large_text(text)
        # Should get 2 content segments, metadata filtered out
        assert len(result) == 2
        assert not any("Score:" in s for s in result)
        assert not any("Date:" in s for s in result)

    def test_micro_segments_merged(self):
        """Segments too small to stand alone are merged with neighbors."""
        text = (
            "Short note one.\n\n"
            "Short note two.\n\n"
            "The knowledge extraction pipeline processes content in monolithic chunks "
            "without any segmentation step before deduplication. This means a 2000-word "
            "paste becomes one giant blob entry in the knowledge store."
        )
        result = segment_large_text(text)
        # The two short notes should be merged (too small alone)
        # The long paragraph stands on its own
        assert len(result) <= 2

    def test_empty_paragraphs_ignored(self):
        """Blank paragraphs don't create empty segments."""
        para1 = (
            "The maturity pipeline promotes entries based on corroboration evidence and source tracking. "
            * 4
        )
        para2 = (
            "The lesson tracker detects absence-as-success after fourteen days of zero regressions observed. "
            * 4
        )
        text = f"{para1}\n\n\n\n\n{para2}"
        result = segment_large_text(text)
        assert len(result) == 2
        assert all(s.strip() for s in result)

    def test_returns_original_if_filtering_eliminates_all(self):
        """If all segments are metadata, return the original content."""
        text = (
            "## Audit Round 8\n"
            "=================\n\n"
            "### Section Header\n"
            "---\n\n"
            "Round 4\n"
            "Score: 9\n"
            "Expert count: 25\n"
            "Focus: knowledge pipeline"
        )
        result = segment_large_text(text)
        assert len(result) == 1
        assert result[0] == text


class TestSegmentationIntegration:
    """Segmentation works correctly with store_knowledge_smart."""

    def test_segmented_storage(self, tmp_path):
        """Large multi-paragraph text stores as multiple entries."""
        import os

        from divineos.core.ledger import init_db
        from divineos.core.knowledge import init_knowledge_table, _get_connection
        from divineos.core.knowledge.extraction import store_knowledge_smart

        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            # Simulate a multi-finding paste
            text = (
                "The stemmed overlap function still uses min-denominator instead of "
                "Dice coefficient. This inflates similarity scores for short entries "
                "and causes false dedup matches between unrelated knowledge.\n\n"
                "The FTS5 query builder joins terms with implicit AND logic which "
                "kills recall when queries contain more than three key terms. "
                "Switching to OR-joined queries would dramatically improve search.\n\n"
                "Seven hardcoded threshold values in the relationship classification "
                "module should be extracted to constants.py. Magic numbers scattered "
                "across the codebase make tuning impossible without code archaeology."
            )
            kid = store_knowledge_smart(
                knowledge_type="OBSERVATION",
                content=text,
                source="SYNTHESIZED",
            )
            assert kid  # Got at least one ID back

            # Check that multiple entries were created
            conn = _get_connection()
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL"
                ).fetchone()[0]
                assert count >= 2, f"Expected multiple entries, got {count}"
            finally:
                conn.close()
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_small_text_not_segmented(self, tmp_path):
        """Small text stores as exactly one entry (no segmentation)."""
        import os

        from divineos.core.ledger import init_db
        from divineos.core.knowledge import init_knowledge_table, _get_connection
        from divineos.core.knowledge.extraction import store_knowledge_smart

        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            kid = store_knowledge_smart(
                knowledge_type="OBSERVATION",
                content="The maturity pipeline promotes entries from RAW to HYPOTHESIS.",
                source="SYNTHESIZED",
            )
            assert kid

            conn = _get_connection()
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL"
                ).fetchone()[0]
                assert count == 1
            finally:
                conn.close()
        finally:
            os.environ.pop("DIVINEOS_DB", None)
