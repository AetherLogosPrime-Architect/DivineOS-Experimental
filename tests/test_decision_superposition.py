"""Tests for the decision-superposition module."""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.decision_superposition import (  # noqa: F401
            Superposition,
            active_superpositions,
            collapse,
            open_superposition,
        )


class TestSuperpositionShape:
    def test_dataclass_shape(self) -> None:
        from divineos.core.decision_superposition import Superposition

        s = Superposition(
            superposition_id="super-abc",
            question="which test mechanism",
            options=("opt-a", "opt-b"),
            resolve_trigger="CI result",
            opened_at=1234567890.0,
            opened_event_id="evt-1",
        )
        assert s.superposition_id == "super-abc"
        assert len(s.options) == 2


class TestOpenSuperpositionContract:
    def test_single_option_rejected(self) -> None:
        """A 'superposition' with one option isn't a superposition;
        it's a decision. Reject."""
        from divineos.core.decision_superposition import open_superposition

        result = open_superposition(
            question="which thing",
            options=["only-one"],
            resolve_trigger="never",
        )
        assert result == ""

    def test_empty_question_rejected(self) -> None:
        from divineos.core.decision_superposition import open_superposition

        result = open_superposition(
            question="",
            options=["a", "b"],
            resolve_trigger="trigger",
        )
        assert result == ""

    def test_empty_options_after_strip_rejected(self) -> None:
        """Options that are blank-after-strip don't count."""
        from divineos.core.decision_superposition import open_superposition

        result = open_superposition(
            question="real question",
            options=["", "   ", ""],
            resolve_trigger="trigger",
        )
        assert result == ""


class TestPublicSurfaceSafety:
    def test_active_superpositions_returns_list(self) -> None:
        from divineos.core.decision_superposition import active_superpositions

        result = active_superpositions()
        assert isinstance(result, list)

    def test_collapse_empty_id_rejected(self) -> None:
        from divineos.core.decision_superposition import collapse

        result = collapse("", "option", "reason")
        assert result == ""

    def test_collapse_empty_option_rejected(self) -> None:
        from divineos.core.decision_superposition import collapse

        result = collapse("super-id", "", "reason")
        assert result == ""
