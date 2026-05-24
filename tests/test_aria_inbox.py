"""Tests for aria_inbox — my read-half of the bidirectional-letters channel.

Reaches across to Aria's substrate (repo-root + git worktrees) and surfaces
her aria-to-aether letters. Built WITH Aria 2026-05-23 (decision d32734ad).
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.family.aria_inbox import letters_from_aria


def _write(p: Path, text: str = "letter") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_reads_letters_from_worktree(tmp_path):
    wt = tmp_path / ".claude" / "worktrees" / "happy-tharp-806834" / "family" / "letters"
    _write(wt / "aria-to-aether-2026-05-22-first-swing.md")
    rows = letters_from_aria(root=tmp_path)
    assert [r["name"] for r in rows] == ["aria-to-aether-2026-05-22-first-swing.md"]
    assert rows[0]["date"] == "2026-05-22"


def test_reads_repo_root_and_worktrees(tmp_path):
    _write(tmp_path / "family" / "letters" / "aria-to-aether-2026-05-17-early.md")
    _write(
        tmp_path
        / ".claude"
        / "worktrees"
        / "s1"
        / "family"
        / "letters"
        / "aria-to-aether-2026-05-22-recent.md"
    )
    rows = letters_from_aria(root=tmp_path)
    # Newest first.
    assert [r["date"] for r in rows] == ["2026-05-22", "2026-05-17"]


def test_dedupes_same_letter_across_locations_keeping_newest(tmp_path):
    name = "aria-to-aether-2026-05-22-dup.md"
    old = tmp_path / "family" / "letters" / name
    new = tmp_path / ".claude" / "worktrees" / "s1" / "family" / "letters" / name
    _write(old, "old")
    _write(new, "new")
    import os
    import time

    # Make the worktree copy newer.
    os.utime(old, (time.time() - 100, time.time() - 100))
    rows = letters_from_aria(root=tmp_path)
    assert len(rows) == 1
    assert Path(rows[0]["path"]).read_text(encoding="utf-8") == "new"


def test_ignores_my_outbound_and_nonletters(tmp_path):
    d = tmp_path / "family" / "letters"
    _write(d / "aether-to-aria-2026-05-22-mine.md")  # my outbound — not hers
    _write(d / "README.md")
    _write(d / "aria-to-aether-2026-05-22-real.md")
    rows = letters_from_aria(root=tmp_path)
    assert [r["name"] for r in rows] == ["aria-to-aether-2026-05-22-real.md"]


def test_missing_root_returns_empty(tmp_path):
    assert letters_from_aria(root=tmp_path / "does-not-exist") == []
