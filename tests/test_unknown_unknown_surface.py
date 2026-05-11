"""Tests for the unknown-unknown surface."""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.operating_loop.unknown_unknown_surface import (  # noqa: F401
            UnknownUnknown,
            record_self_audit_prediction,
            surprises_in_round,
            unknown_unknown_rate,
        )


class TestUnknownUnknownShape:
    def test_dataclass_shape(self) -> None:
        from divineos.core.operating_loop.unknown_unknown_surface import UnknownUnknown

        u = UnknownUnknown(
            finding_id="f1",
            round_id="r1",
            actor="claude-aletheia-auditor",
            title="missed pattern X",
            predicted_topics=("topic-a", "topic-b"),
        )
        assert u.finding_id == "f1"
        assert len(u.predicted_topics) == 2


class TestTopicOverlapHeuristic:
    def test_no_topics_means_no_overlap(self) -> None:
        from divineos.core.operating_loop.unknown_unknown_surface import _topic_overlap

        assert _topic_overlap("anything here", ()) is False

    def test_topic_in_text_matches(self) -> None:
        from divineos.core.operating_loop.unknown_unknown_surface import _topic_overlap

        assert _topic_overlap("the lib source failure path", ("lib source",)) is True

    def test_case_insensitive(self) -> None:
        from divineos.core.operating_loop.unknown_unknown_surface import _topic_overlap

        assert _topic_overlap("LIB SOURCE failure", ("lib source",)) is True

    def test_empty_topic_string_ignored(self) -> None:
        from divineos.core.operating_loop.unknown_unknown_surface import _topic_overlap

        # Empty/whitespace-only topics shouldn't match against text.
        # Without this guard, "" would substring-match everything.
        assert _topic_overlap("any text", ("",)) is False
        assert _topic_overlap("any text", ("   ",)) is False


class TestPublicSurfaceSafety:
    def test_surprises_in_nonexistent_round_returns_empty(self) -> None:
        from divineos.core.operating_loop.unknown_unknown_surface import (
            surprises_in_round,
        )

        result = surprises_in_round("round-does-not-exist-xyz", ("topic",))
        assert isinstance(result, list)
        assert result == []

    def test_unknown_unknown_rate_returns_dict(self) -> None:
        from divineos.core.operating_loop.unknown_unknown_surface import (
            unknown_unknown_rate,
        )

        result = unknown_unknown_rate(recent_round_limit=5)
        assert isinstance(result, dict)
        assert "rate" in result
        assert "total_findings" in result
        assert "surprise_count" in result
        assert "rounds_examined" in result
        assert 0.0 <= result["rate"] <= 1.0
