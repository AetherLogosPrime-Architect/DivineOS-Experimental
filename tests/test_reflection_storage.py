"""Tests for reflection_storage module (Phase 2A of shoggoth-metrics redesign)."""

from __future__ import annotations

import pytest


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.reflection_storage import (  # noqa: F401
            Reflection,
            format_reflection,
            format_session_reflections,
            get_recent_reflections,
            get_reflections_for_session,
            init_reflection_table,
            save_reflection,
        )


class TestReflectionDataclassShape:
    def test_construction(self) -> None:
        from divineos.core.reflection_storage import Reflection

        r = Reflection(
            reflection_id="refl-abc123",
            session_id="sess-xyz",
            recorded_at=1234.5,
            spectrum="truthfulness",
            reflection_text="I held this honestly.",
            evidence_refs=[{"type": "observation", "id": "obs-1", "label": "evidence"}],
        )
        assert r.reflection_id == "refl-abc123"
        assert r.spectrum == "truthfulness"
        assert len(r.evidence_refs) == 1


class TestSaveReflection:
    def test_save_returns_id_with_refl_prefix(self) -> None:
        from divineos.core.reflection_storage import save_reflection

        rid = save_reflection(
            session_id="test-sess-1",
            spectrum="truthfulness",
            reflection_text="Held honest this session.",
        )
        assert rid.startswith("refl-")
        assert len(rid) > len("refl-")

    def test_invalid_spectrum_raises(self) -> None:
        from divineos.core.reflection_storage import save_reflection

        with pytest.raises(ValueError, match="Unknown spectrum"):
            save_reflection(
                session_id="test-sess-2",
                spectrum="nonexistent_virtue",
                reflection_text="text",
            )

    def test_empty_text_raises(self) -> None:
        """Substrate stores what the agent said, not silence — empty text is rejected."""
        from divineos.core.reflection_storage import save_reflection

        with pytest.raises(ValueError, match="empty"):
            save_reflection(
                session_id="test-sess-3",
                spectrum="truthfulness",
                reflection_text="",
            )

    def test_whitespace_only_text_raises(self) -> None:
        from divineos.core.reflection_storage import save_reflection

        with pytest.raises(ValueError, match="empty"):
            save_reflection(
                session_id="test-sess-4",
                spectrum="truthfulness",
                reflection_text="    \n\t  ",
            )

    def test_save_with_evidence_refs(self) -> None:
        from divineos.core.reflection_storage import (
            get_reflections_for_session,
            save_reflection,
        )

        rid = save_reflection(
            session_id="test-sess-evi",
            spectrum="confidence",
            reflection_text="Calibrated this session.",
            evidence_refs=[
                {"type": "observation", "id": "obs-1", "label": "compass obs"},
                {"type": "knowledge", "id": "k-1", "label": "principle"},
            ],
        )
        assert rid

        # Retrieve and verify evidence_refs round-tripped via JSON column.
        refls = get_reflections_for_session("test-sess-evi")
        matching = [r for r in refls if r.reflection_id == rid]
        assert len(matching) == 1
        assert len(matching[0].evidence_refs) == 2
        assert matching[0].evidence_refs[0]["type"] == "observation"


class TestRetrieve:
    def test_get_reflections_for_session_returns_list(self) -> None:
        from divineos.core.reflection_storage import get_reflections_for_session

        result = get_reflections_for_session("definitely-nonexistent-session-9999")
        assert isinstance(result, list)
        assert result == []

    def test_get_reflections_returns_saved(self) -> None:
        from divineos.core.reflection_storage import (
            get_reflections_for_session,
            save_reflection,
        )

        sid = "test-sess-retrieve"
        save_reflection(sid, "truthfulness", "first reflection")
        save_reflection(sid, "humility", "second reflection")

        refls = get_reflections_for_session(sid)
        assert len(refls) >= 2  # at least these two
        spectrums = {r.spectrum for r in refls}
        assert "truthfulness" in spectrums
        assert "humility" in spectrums

    def test_get_recent_returns_list(self) -> None:
        from divineos.core.reflection_storage import get_recent_reflections

        result = get_recent_reflections("truthfulness", limit=5)
        assert isinstance(result, list)

    def test_get_recent_invalid_spectrum_returns_empty(self) -> None:
        from divineos.core.reflection_storage import get_recent_reflections

        result = get_recent_reflections("nonexistent", limit=5)
        assert result == []


class TestFormatReflection:
    def test_format_includes_spectrum_and_text(self) -> None:
        from divineos.core.reflection_storage import Reflection, format_reflection

        r = Reflection(
            reflection_id="refl-fmt1",
            session_id="sess-fmt",
            recorded_at=1.0,
            spectrum="truthfulness",
            reflection_text="A reflection",
            evidence_refs=[],
        )
        output = format_reflection(r)
        assert "TRUTHFULNESS" in output
        assert "A reflection" in output
        assert "refl-fmt" in output  # truncated ID shown

    def test_format_includes_evidence_pointers(self) -> None:
        from divineos.core.reflection_storage import Reflection, format_reflection

        r = Reflection(
            reflection_id="refl-fmt2",
            session_id="sess-fmt",
            recorded_at=1.0,
            spectrum="truthfulness",
            reflection_text="text",
            evidence_refs=[
                {"type": "observation", "id": "obs-1", "label": "compass evidence"},
            ],
        )
        output = format_reflection(r)
        assert "observation:obs-1" in output
        assert "compass evidence" in output


class TestFormatSessionReflections:
    def test_empty_session_message(self) -> None:
        from divineos.core.reflection_storage import format_session_reflections

        output = format_session_reflections("definitely-empty-session-8888")
        assert "No reflections" in output

    def test_format_with_reflections(self) -> None:
        from divineos.core.reflection_storage import (
            format_session_reflections,
            save_reflection,
        )

        sid = "test-sess-fmt"
        save_reflection(sid, "truthfulness", "reflection one")

        output = format_session_reflections(sid)
        assert "TRUTHFULNESS" in output
        assert "reflection one" in output


class TestIdempotentInit:
    def test_init_reflection_table_safe_to_call_repeatedly(self) -> None:
        """init_reflection_table is called inside every save/get — must be idempotent."""
        from divineos.core.reflection_storage import init_reflection_table

        # Should not raise on repeated calls.
        init_reflection_table()
        init_reflection_table()
        init_reflection_table()
