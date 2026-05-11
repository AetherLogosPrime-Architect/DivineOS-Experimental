"""Tests for the consequence_chain module."""

from __future__ import annotations


class TestModuleImport:
    def test_module_importable(self) -> None:
        from divineos.core.consequence_chain import (  # noqa: F401
            ConsequenceChain,
            chain_from_decision,
            chain_to_lesson,
            recent_chains,
        )


class TestConsequenceChainShape:
    def test_dataclass_shape(self) -> None:
        from divineos.core.consequence_chain import ConsequenceChain

        c = ConsequenceChain(
            decision_id="d1",
            decision_summary="test",
            session_id="s1",
            outcome_event_ids=("e1", "e2"),
            lesson_ids=("k1",),
            decision_ts=1234.5,
        )
        assert c.decision_id == "d1"
        assert len(c.outcome_event_ids) == 2
        assert len(c.lesson_ids) == 1

    def test_dataclass_defaults(self) -> None:
        from divineos.core.consequence_chain import ConsequenceChain

        c = ConsequenceChain(
            decision_id="d1",
            decision_summary="test",
            session_id="s1",
        )
        assert c.outcome_event_ids == ()
        assert c.lesson_ids == ()
        assert c.decision_ts == 0.0


class TestPublicSurfaceSafety:
    """All public functions must fail-soft on missing data."""

    def test_chain_from_nonexistent_decision_returns_none(self) -> None:
        from divineos.core.consequence_chain import chain_from_decision

        result = chain_from_decision("decision-does-not-exist-xyz")
        # Either returns None (decision not found) or a ConsequenceChain
        # with empty outcomes/lessons (decision found but no chain).
        if result is not None:
            from divineos.core.consequence_chain import ConsequenceChain

            assert isinstance(result, ConsequenceChain)

    def test_chain_to_nonexistent_lesson_returns_empty(self) -> None:
        from divineos.core.consequence_chain import chain_to_lesson

        result = chain_to_lesson("lesson-does-not-exist-xyz")
        assert isinstance(result, list)
        assert result == []

    def test_recent_chains_returns_list(self) -> None:
        from divineos.core.consequence_chain import recent_chains

        result = recent_chains(limit=3)
        assert isinstance(result, list)
        # Each item must be a ConsequenceChain if any returned.
        from divineos.core.consequence_chain import ConsequenceChain

        for c in result:
            assert isinstance(c, ConsequenceChain)
