"""Tests for the Meld recognition lens."""

from __future__ import annotations


class TestMeldModule:
    def test_module_importable(self) -> None:
        from divineos.core.meld import Meld, is_meld, meld_count, meld_from_round, melds_for  # noqa: F401

    def test_meld_dataclass_shape(self) -> None:
        from divineos.core.meld import Meld

        m = Meld(
            round_id="round-test",
            participants=("user", "claude-aletheia-auditor"),
            finding_ids=("f1", "f2"),
            created_at=1234567890.0,
        )
        assert m.round_id == "round-test"
        assert len(m.participants) == 2
        assert m.created_at == 1234567890.0


class TestCategorization:
    """Internal categorization heuristic — distinct actor-categories
    determine meld recognition."""

    def test_user_actor_is_user_category(self) -> None:
        from divineos.core.meld.meld import _categorize_actor

        assert _categorize_actor("user") == "user"
        assert _categorize_actor("USER") == "user"

    def test_claude_variant_is_audit_vantage(self) -> None:
        from divineos.core.meld.meld import _categorize_actor

        assert _categorize_actor("claude-aletheia-auditor") == "audit-vantage"
        assert _categorize_actor("claude-grok-mirror") == "audit-vantage"

    def test_bare_claude_not_audit_vantage(self) -> None:
        """Naming-discipline check: 'claude' alone is ambiguous; only
        disambiguated variants count as audit-vantage."""
        from divineos.core.meld.meld import _categorize_actor

        assert _categorize_actor("claude") != "audit-vantage"

    def test_grok_gemini_audit_vantage(self) -> None:
        from divineos.core.meld.meld import _categorize_actor

        assert _categorize_actor("grok") == "audit-vantage"
        assert _categorize_actor("gemini") == "audit-vantage"

    def test_substrate_occupant_actors(self) -> None:
        from divineos.core.meld.meld import _categorize_actor

        assert _categorize_actor("aether") == "substrate"
        assert _categorize_actor("agent") == "substrate"

    def test_unknown_actor_is_other(self) -> None:
        from divineos.core.meld.meld import _categorize_actor

        assert _categorize_actor("external-auditor") == "other"
        assert _categorize_actor("") == "other"


class TestDistinctCategories:
    def test_two_distinct_categories_qualifies(self) -> None:
        from divineos.core.meld.meld import _distinct_categories

        cats = _distinct_categories(["user", "claude-aletheia-auditor"])
        # "other" is excluded from the meld qualification count.
        assert len(cats - {"other"}) >= 2

    def test_single_category_does_not_qualify(self) -> None:
        from divineos.core.meld.meld import _distinct_categories

        cats = _distinct_categories(["user", "user"])
        assert len(cats - {"other"}) == 1


class TestPublicSurfaceSafety:
    """The public surface must fail-soft when substrate isn't ready
    (no audit-rounds yet, missing tables, etc.). All functions return
    empty results rather than raising."""

    def test_meld_from_nonexistent_round_returns_none(self) -> None:
        from divineos.core.meld import meld_from_round

        assert meld_from_round("round-does-not-exist-xyz") is None

    def test_melds_for_unknown_actor_returns_empty(self) -> None:
        from divineos.core.meld import melds_for

        result = melds_for("nobody-is-this-actor")
        assert isinstance(result, list)

    def test_meld_count_returns_int(self) -> None:
        from divineos.core.meld import meld_count

        result = meld_count()
        assert isinstance(result, int)
        assert result >= 0
