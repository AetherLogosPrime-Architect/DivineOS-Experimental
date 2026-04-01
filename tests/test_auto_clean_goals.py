"""Tests for automatic goal cleanup at session end."""

import json
import time
from pathlib import Path
from unittest.mock import patch

from divineos.core.hud_state import auto_clean_goals


class TestAutoCleanGoals:
    """Goals should be auto-cleaned at SESSION_END."""

    def _write_goals(self, tmp_path: Path, goals: list[dict]) -> None:
        (tmp_path / "active_goals.json").write_text(json.dumps(goals))

    def _read_goals(self, tmp_path: Path) -> list[dict]:
        return json.loads((tmp_path / "active_goals.json").read_text())

    def test_archives_stale_goals(self, tmp_path: Path) -> None:
        """Stale goals are removed from the list entirely."""
        old_time = time.time() - (4 * 86400)  # 4 days ago
        self._write_goals(
            tmp_path,
            [
                {"text": "Old stale goal", "status": "active", "added_at": old_time},
                {"text": "Fresh goal", "status": "active", "added_at": time.time()},
            ],
        )

        with patch("divineos.core.hud_state._ensure_hud_dir", return_value=tmp_path):
            result = auto_clean_goals(max_age_days=3.0)

        goals = self._read_goals(tmp_path)
        assert result["stale_archived"] == 1
        # Stale goal removed, only fresh goal remains
        assert len(goals) == 1
        assert goals[0]["text"] == "Fresh goal"
        assert goals[0]["status"] == "active"

    def test_clears_completed_goals(self, tmp_path: Path) -> None:
        """Completed goals are removed from the list."""
        self._write_goals(
            tmp_path,
            [
                {"text": "Done goal", "status": "done", "added_at": time.time()},
                {"text": "Active goal", "status": "active", "added_at": time.time()},
            ],
        )

        with patch("divineos.core.hud_state._ensure_hud_dir", return_value=tmp_path):
            result = auto_clean_goals()

        goals = self._read_goals(tmp_path)
        assert result["completed_cleared"] == 1
        assert len(goals) == 1
        assert goals[0]["text"] == "Active goal"

    def test_deduplicates_similar_goals(self, tmp_path: Path) -> None:
        """Near-duplicate active goals keep only the newest."""
        now = time.time()
        self._write_goals(
            tmp_path,
            [
                {
                    "text": "Build periodic engagement enforcement",
                    "status": "active",
                    "added_at": now - 100,
                },
                {
                    "text": "Build periodic engagement enforcement gate",
                    "status": "active",
                    "added_at": now,
                },
            ],
        )

        with patch("divineos.core.hud_state._ensure_hud_dir", return_value=tmp_path):
            result = auto_clean_goals()

        goals = self._read_goals(tmp_path)
        assert result["deduped"] == 1
        # Older duplicate removed, only newer one remains
        assert len(goals) == 1
        assert goals[0]["status"] == "active"

    def test_no_changes_when_clean(self, tmp_path: Path) -> None:
        """No changes when goals are already clean."""
        self._write_goals(
            tmp_path,
            [
                {"text": "Current goal", "status": "active", "added_at": time.time()},
            ],
        )

        with patch("divineos.core.hud_state._ensure_hud_dir", return_value=tmp_path):
            result = auto_clean_goals()

        assert result["stale_archived"] == 0
        assert result["deduped"] == 0
        assert result["completed_cleared"] == 0

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        """Returns zeros when no goals file exists."""
        with patch("divineos.core.hud_state._ensure_hud_dir", return_value=tmp_path):
            result = auto_clean_goals()
        assert result["stale_archived"] == 0
        assert result["deduped"] == 0

    def test_preserves_done_goals(self, tmp_path: Path) -> None:
        """Already-done goals are left alone."""
        old_time = time.time() - (10 * 86400)
        self._write_goals(
            tmp_path,
            [
                {"text": "Old done goal", "status": "done", "added_at": old_time},
            ],
        )

        with patch("divineos.core.hud_state._ensure_hud_dir", return_value=tmp_path):
            result = auto_clean_goals()

        assert result["stale_archived"] == 0
