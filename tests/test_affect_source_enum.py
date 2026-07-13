"""F-VAD-1 discipline tests — mandatory source enum on affect_log.

Per prereg-49130c8e7653. External auditor found affect_log was a mixed
channel (self-report + session-derived + decision-fallback sharing one
table with only tag-based separation). This test suite locks the four
properties of the fix:

1. log_affect raises when source is omitted (raise-on-absence)
2. log_affect raises when source is not in the enum (rejects invalid)
3. log_affect accepts each of the four valid enum values
4. get_affect_history returns the source field
"""

from __future__ import annotations

import pytest

from divineos.core.affect import AFFECT_SOURCES, get_affect_history, log_affect


class TestSourceEnumRequired:
    """F-VAD-1: raise-on-absence forces every write to name its provenance."""

    def test_omit_source_raises(self) -> None:
        # source is keyword-only with no default; call without it must fail.
        with pytest.raises(TypeError):
            log_affect(0.5, 0.5, description="no source given")  # type: ignore[call-arg]

    def test_invalid_source_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="source must be one of"):
            log_affect(0.5, 0.5, source="invented_channel", description="bad source")

    def test_empty_string_source_raises(self) -> None:
        with pytest.raises(ValueError, match="source must be one of"):
            log_affect(0.5, 0.5, source="", description="empty source")


class TestSourceEnumAcceptsAllValid:
    """Every enum value must be accepted for a write."""

    @pytest.mark.parametrize(
        "src",
        ["self_filed", "session_derived", "decision_fallback", "ambiguous"],
    )
    def test_accepts_each_enum_value(self, src: str) -> None:
        entry_id = log_affect(0.3, 0.4, source=src, description=f"test entry for {src}")
        assert entry_id  # returns a non-empty entry id

    def test_enum_frozenset_contents(self) -> None:
        assert AFFECT_SOURCES == frozenset(
            {"self_filed", "session_derived", "decision_fallback", "ambiguous"}
        )


class TestSourceReturnedInHistory:
    """Consumers reading affect_log see the source column so they can filter."""

    def test_source_field_in_history_dict(self) -> None:
        log_affect(0.7, 0.5, source="self_filed", description="history round-trip test")
        hist = get_affect_history(limit=1)
        assert len(hist) >= 1
        assert "source" in hist[0]
        assert hist[0]["source"] == "self_filed"

    def test_history_preserves_source_across_writes(self) -> None:
        log_affect(0.1, 0.1, source="session_derived", description="a")
        log_affect(0.2, 0.2, source="self_filed", description="b")
        hist = get_affect_history(limit=2)
        sources = [row["source"] for row in hist[:2]]
        assert "self_filed" in sources
        assert "session_derived" in sources
