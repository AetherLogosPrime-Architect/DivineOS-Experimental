"""Tests for the council invocation-balance briefing surface."""

from __future__ import annotations

from unittest.mock import patch

from divineos.core import council_balance_surface as cbs


class TestSilentCases:
    def test_no_consultations_returns_empty(self) -> None:
        with patch(
            "divineos.core.council.consultation_log.list_recent_consultations",
            return_value=[],
        ):
            assert cbs.format_for_briefing() == ""

    def test_below_min_consultations_returns_empty(self) -> None:
        with patch(
            "divineos.core.council.consultation_log.list_recent_consultations",
            return_value=[{"selected_experts": ["dennett"]}] * (cbs.MIN_CONSULTATIONS - 1),
        ):
            assert cbs.format_for_briefing() == ""

    def test_empty_engine_roster_returns_empty(self) -> None:
        recent = [{"selected_experts": ["dennett"]}] * 10
        with (
            patch(
                "divineos.core.council.consultation_log.list_recent_consultations",
                return_value=recent,
            ),
            patch("divineos.core.council.engine.get_council_engine") as ge,
        ):
            ge.return_value.experts = {}
            assert cbs.format_for_briefing() == ""


class TestSurfaceContent:
    def test_shows_most_invoked_and_never_invoked(self) -> None:
        recent = [
            {"selected_experts": ["dennett", "hofstadter", "feynman"]},
            {"selected_experts": ["dennett", "feynman"]},
            {"selected_experts": ["dennett", "hofstadter"]},
        ]
        roster = [
            "dennett",
            "hofstadter",
            "feynman",
            "angelou",
            "schneier",
            "taleb",
            "yudkowsky",
        ]
        with (
            patch(
                "divineos.core.council.consultation_log.list_recent_consultations",
                return_value=recent,
            ),
            patch("divineos.core.council.engine.get_council_engine") as ge,
        ):
            ge.return_value.experts = {n: object() for n in roster}
            out = cbs.format_for_briefing()

        assert "council balance" in out
        assert "most-invoked: dennett (3)" in out
        # never-invoked block names some untouched experts
        assert "never-invoked" in out
        for name in ("angelou", "schneier", "taleb", "yudkowsky"):
            assert name in out
        # Deterministic candidate is alphabetically first never-invoked.
        assert "consider for next walk: angelou" in out

    def test_rarely_invoked_branch_when_no_never_invoked(self) -> None:
        # All four experts get at least one invocation.
        recent = [
            {"selected_experts": ["dennett", "hofstadter"]},
            {"selected_experts": ["dennett", "feynman"]},
            {"selected_experts": ["dennett", "angelou"]},
        ]
        roster = ["dennett", "hofstadter", "feynman", "angelou"]
        with (
            patch(
                "divineos.core.council.consultation_log.list_recent_consultations",
                return_value=recent,
            ),
            patch("divineos.core.council.engine.get_council_engine") as ge,
        ):
            ge.return_value.experts = {n: object() for n in roster}
            out = cbs.format_for_briefing()

        assert "council balance" in out
        assert "most-invoked: dennett" in out
        assert "rarely-invoked" in out
        assert "consider for next walk:" in out
        assert "never-invoked" not in out

    def test_failsoft_on_consultation_log_failure(self) -> None:
        with patch(
            "divineos.core.council.consultation_log.list_recent_consultations",
            side_effect=RuntimeError("db down"),
        ):
            # Briefing must never break on this surface — even an
            # unexpected exception type returns empty string.
            assert cbs.format_for_briefing() == ""
