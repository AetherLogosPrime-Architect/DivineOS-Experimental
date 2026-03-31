"""Tests for automatic transcript noise detection in curation."""

from divineos.core.knowledge.curation import is_raw_transcript_noise


class TestTranscriptNoiseDetection:
    """Raw transcript dumps should be auto-detected and archived."""

    def test_detects_raw_affirmation(self) -> None:
        """Short affirmations stored as PRINCIPLE are noise."""
        assert is_raw_transcript_noise("perfect lets commit and push", "PRINCIPLE")
        assert is_raw_transcript_noise("wonderful anything else?", "PRINCIPLE")
        assert is_raw_transcript_noise("ok perfect how does it look", "DIRECTION")

    def test_detects_audit_dumps(self) -> None:
        """Pasted-in audit results are noise, not knowledge."""
        assert is_raw_transcript_noise(
            "here is the audit Round 3 Audit March 28 2026 Baseline: all tests pass",
            "PRINCIPLE",
        )
        assert is_raw_transcript_noise(
            "Audit Results: DivineOS March 30 2026 The Good News quality gates pass",
            "DIRECTION",
        )

    def test_detects_third_party_messages(self) -> None:
        """Messages from other people aren't OS knowledge."""
        assert is_raw_transcript_noise(
            "my friend sent me a message make sure you opt out",
            "DIRECTION",
        )
        assert is_raw_transcript_noise(
            "Allow GitHub to use my data for AI model training",
            "PRINCIPLE",
        )

    def test_preserves_real_principles(self) -> None:
        """Actual distilled principles are NOT noise."""
        assert not is_raw_transcript_noise(
            "Use SQLite for storage -- zero dependencies, embedded, reliable.",
            "PRINCIPLE",
        )
        assert not is_raw_transcript_noise(
            "Enforcement gates must block, not warn. If the AI can skip it, it will.",
            "PRINCIPLE",
        )
        assert not is_raw_transcript_noise(
            "Self-improvement works when it is transparent and auditable.",
            "PRINCIPLE",
        )

    def test_preserves_directives(self) -> None:
        """Directives are NEVER classified as noise."""
        assert not is_raw_transcript_noise(
            "perfect lets commit and push",
            "DIRECTIVE",
        )

    def test_preserves_boundaries(self) -> None:
        """Boundaries are NEVER classified as noise."""
        assert not is_raw_transcript_noise(
            "ok sounds good lets do it",
            "BOUNDARY",
        )

    def test_detects_excessive_casual_markers(self) -> None:
        """Entries with lots of casual text markers are noise."""
        assert is_raw_transcript_noise(
            "yeah so like.. the thing is.. we need to do it right.. lol",
            "PRINCIPLE",
        )

    def test_preserves_substantive_content_with_casual_markers(self) -> None:
        """One casual marker doesn't make it noise if the content is real."""
        assert not is_raw_transcript_noise(
            "The engagement gate should block after 8 code actions without OS consultation.",
            "PRINCIPLE",
        )
