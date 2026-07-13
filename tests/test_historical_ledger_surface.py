"""Tests for historical_ledger_surface — points worktree sessions at parent ledger."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from divineos.core import historical_ledger_surface as hls


def _make_ledger(path: Path, events: list[tuple[str, float]]) -> None:
    """Create a minimal ledger DB at ``path`` with given (event_type, timestamp)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    # Match production schema exactly per test_schema_sync requirement.
    conn.execute(
        "CREATE TABLE system_events (event_id TEXT, timestamp REAL, event_type TEXT, actor TEXT, payload TEXT, content_hash TEXT, prior_hash TEXT, chain_hash TEXT)"
    )
    for i, (et, ts) in enumerate(events):
        conn.execute(
            "INSERT INTO system_events VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)",
            (f"e{i}", ts, et, "test", "{}", f"h{i}"),
        )
    conn.commit()
    conn.close()


def _make_worktree(parent: Path, name: str) -> Path:
    """Create a worktree-shaped directory with .git file pointing at parent."""
    worktree = parent / ".claude" / "worktrees" / name
    worktree.mkdir(parents=True)
    # Worktree .git file format: "gitdir: /abs/path/to/parent/.git/worktrees/<name>"
    gitdir = parent / ".git" / "worktrees" / name
    gitdir.mkdir(parents=True)
    (worktree / ".git").write_text(f"gitdir: {gitdir.resolve()}", encoding="utf-8")
    return worktree


class TestWorktreeDetection:
    def test_returns_empty_for_non_worktree(self, tmp_path: Path) -> None:
        # Plain directory, no .git file
        lines = hls.briefing_lines(start=tmp_path)
        assert lines == []

    def test_returns_lines_when_in_worktree(self, tmp_path: Path) -> None:
        # Set up parent repo with .git directory and a ledger
        (tmp_path / ".git").mkdir()
        _make_ledger(
            tmp_path / "src" / "data" / "event_ledger.db",
            [("USER_INPUT", 1.0), ("USER_INPUT", 2.0), ("TOOL_CALL", 3.0)],
        )

        # Set up worktree
        worktree = _make_worktree(tmp_path, "test-worktree")
        _make_ledger(
            worktree / "src" / "data" / "event_ledger.db",
            [("USER_INPUT", 100.0)],
        )

        lines = hls.briefing_lines(start=worktree)
        joined = "\n".join(lines)
        assert "HISTORICAL LEDGER" in joined
        assert "3 events" in joined or "3," in joined
        assert "user inputs" in joined.lower() or "user_inputs" in joined.lower()


class TestUnresolvedCases:
    def test_unresolved_when_git_file_malformed(self, tmp_path: Path) -> None:
        worktree = tmp_path / "wt"
        worktree.mkdir()
        (worktree / ".git").write_text("not a gitdir line", encoding="utf-8")
        lines = hls.briefing_lines(start=worktree)
        joined = "\n".join(lines)
        assert "UNRESOLVED" in joined

    def test_unresolved_when_parent_ledger_missing(self, tmp_path: Path) -> None:
        # Parent has .git but NO ledger
        (tmp_path / ".git").mkdir()
        worktree = _make_worktree(tmp_path, "test-worktree")
        lines = hls.briefing_lines(start=worktree)
        joined = "\n".join(lines)
        assert "UNRESOLVED" in joined


class TestRender:
    def test_render_empty_for_non_worktree(self, tmp_path: Path) -> None:
        assert hls.render(start=tmp_path) == ""

    def test_render_joins_with_newlines(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        _make_ledger(
            tmp_path / "src" / "data" / "event_ledger.db",
            [("USER_INPUT", 1.0)],
        )
        worktree = _make_worktree(tmp_path, "wt")
        rendered = hls.render(start=worktree)
        assert "\n" in rendered
        assert rendered.startswith("HISTORICAL LEDGER")
