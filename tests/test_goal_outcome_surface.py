"""Tests for the goal-outcome briefing surface (action-loop closure)."""

from __future__ import annotations

import json
import time
from unittest.mock import patch

from divineos.core import goal_outcome_surface as gos


def _write_outcomes(tmp_path, outcomes):
    p = tmp_path / "goal_outcomes.json"
    p.write_text(json.dumps(outcomes), encoding="utf-8")
    return p


class TestSilentCases:
    def test_no_outcomes_file(self, tmp_path) -> None:
        with patch.object(gos, "_outcomes_path", return_value=tmp_path / "absent.json"):
            assert gos.format_for_briefing() == ""

    def test_below_min_to_surface(self, tmp_path) -> None:
        # Only one stale-archival in window — under MIN_TO_SURFACE
        now = time.time()
        outcomes = [
            {
                "text": "lonely goal",
                "added_at": now - 86400,
                "archived_at": now - 3600,
                "outcome": "stale_archived",
            }
        ]
        p = _write_outcomes(tmp_path, outcomes)
        with patch.object(gos, "_outcomes_path", return_value=p):
            assert gos.format_for_briefing() == ""

    def test_only_completed_outcomes_silent(self, tmp_path) -> None:
        # complete_goal-shaped outcomes shouldn't be surfaced even if many
        now = time.time()
        outcomes = [
            {
                "text": f"completed goal {i}",
                "added_at": now - 86400,
                "archived_at": now - 3600,
                "outcome": "completed",
            }
            for i in range(5)
        ]
        p = _write_outcomes(tmp_path, outcomes)
        with patch.object(gos, "_outcomes_path", return_value=p):
            assert gos.format_for_briefing() == ""

    def test_outdated_entries_dont_count(self, tmp_path) -> None:
        # Stale-archived but archived more than SURFACE_WINDOW_DAYS ago
        now = time.time()
        old_age = (gos.SURFACE_WINDOW_DAYS + 1) * 86400
        outcomes = [
            {
                "text": f"old goal {i}",
                "added_at": now - old_age - 86400,
                "archived_at": now - old_age,
                "outcome": "stale_archived",
            }
            for i in range(5)
        ]
        p = _write_outcomes(tmp_path, outcomes)
        with patch.object(gos, "_outcomes_path", return_value=p):
            assert gos.format_for_briefing() == ""

    def test_corrupt_outcomes_file_returns_empty(self, tmp_path) -> None:
        p = tmp_path / "goal_outcomes.json"
        p.write_text("{not json", encoding="utf-8")
        with patch.object(gos, "_outcomes_path", return_value=p):
            assert gos.format_for_briefing() == ""

    def test_non_list_json_returns_empty(self, tmp_path) -> None:
        p = tmp_path / "goal_outcomes.json"
        p.write_text('{"unexpected": "shape"}', encoding="utf-8")
        with patch.object(gos, "_outcomes_path", return_value=p):
            assert gos.format_for_briefing() == ""


class TestSurfaceContent:
    def test_shows_recent_stale_archivals(self, tmp_path) -> None:
        now = time.time()
        outcomes = [
            {
                "text": "Build per-session briefing-load gate",
                "added_at": now - 2 * 86400,
                "archived_at": now - 86400,
                "outcome": "stale_archived",
            },
            {
                "text": "Continue strip-mine reading pass",
                "added_at": now - 3 * 86400,
                "archived_at": now - 2 * 86400,
                "outcome": "stale_archived",
            },
        ]
        p = _write_outcomes(tmp_path, outcomes)
        with patch.object(gos, "_outcomes_path", return_value=p):
            out = gos.format_for_briefing()
        assert "goals that aged out without progression" in out
        assert "Build per-session briefing-load gate" in out
        assert "Continue strip-mine reading pass" in out
        assert "consider:" in out

    def test_caps_at_max_listed(self, tmp_path) -> None:
        now = time.time()
        outcomes = [
            {
                "text": f"goal {i}",
                "added_at": now - 86400,
                "archived_at": now - 3600 - i,
                "outcome": "stale_archived",
            }
            for i in range(gos.MAX_LISTED + 3)
        ]
        p = _write_outcomes(tmp_path, outcomes)
        with patch.object(gos, "_outcomes_path", return_value=p):
            out = gos.format_for_briefing()
        # Only MAX_LISTED entries shown
        assert out.count('"goal') == gos.MAX_LISTED
        assert f"+{3} more this window" in out

    def test_newest_first_ordering(self, tmp_path) -> None:
        now = time.time()
        outcomes = [
            {
                "text": "older",
                "added_at": now - 4 * 86400,
                "archived_at": now - 3 * 86400,
                "outcome": "stale_archived",
            },
            {
                "text": "newer",
                "added_at": now - 2 * 86400,
                "archived_at": now - 86400,
                "outcome": "stale_archived",
            },
        ]
        p = _write_outcomes(tmp_path, outcomes)
        with patch.object(gos, "_outcomes_path", return_value=p):
            out = gos.format_for_briefing()
        # "newer" appears before "older" in output
        assert out.index('"newer"') < out.index('"older"')


class TestFormatAge:
    def test_minutes(self) -> None:
        assert gos._format_age(120) == "2m"

    def test_hours(self) -> None:
        assert gos._format_age(7200) == "2h"

    def test_days(self) -> None:
        assert gos._format_age(2 * 86400) == "2d"


class TestFailSoft:
    def test_unexpected_exception_returns_empty(self, tmp_path) -> None:
        # Force an unexpected exception type
        with patch.object(gos, "_outcomes_path", side_effect=RuntimeError("filesystem down")):
            assert gos.format_for_briefing() == ""
