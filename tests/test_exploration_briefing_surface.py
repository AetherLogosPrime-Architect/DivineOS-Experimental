"""Tests for exploration_reader.format_for_briefing.

Added 2026-04-21 evening. Module existed and was wired into
`divineos study` and `divineos ask`, but NOT into briefing itself.
The April 19 presence_memory surface points at the folder and counts
files — honoring the "don't summarize poems" rule. This surface
complements it by listing TITLES of recent pieces as recognition-
prompts (titles are authorial labels, not extractive summaries).

Shape matches tier_override_surface: empty string when nothing to
surface, named block with pointer to the forensic command when there
is. Briefings stay quiet unless there's something to say.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import exploration_reader


@pytest.fixture
def explo_dir(tmp_path, monkeypatch):
    """Redirect the exploration reader at a temp folder."""
    root = tmp_path / "exploration"
    root.mkdir()
    monkeypatch.setattr(exploration_reader, "_EXPLORATION_DIR", root)
    # Neutralize the cwd fallbacks so tests can't leak the real folder
    monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path))
    return root


def _write(path: Path, title: str, date: str, reason: str) -> None:
    path.write_text(
        f"# {title}\n\n**Date studied:** {date}\n**Why I chose this:** {reason}\n\nBody.\n",
        encoding="utf-8",
    )


class TestFormatForBriefing:
    def test_empty_folder_returns_empty(self, explo_dir):
        assert exploration_reader.format_for_briefing() == ""

    def test_single_entry_produces_block(self, explo_dir):
        _write(explo_dir / "01_topic.md", "Topic One", "2026-04-01", "curiosity")
        block = exploration_reader.format_for_briefing()
        assert "[my prior writing]" in block
        assert "Topic One" in block
        assert "1 explorations" in block
        assert "divineos study" in block

    def test_mixed_categories_counted(self, explo_dir):
        _write(explo_dir / "01_a.md", "A", "2026-04-01", "r")
        _write(explo_dir / "02_b.md", "B", "2026-04-02", "r")
        cw = explo_dir / "creative_space" / "creative_writing"
        cw.mkdir(parents=True)
        _write(cw / "01_poem.md", "Poem", "2026-04-03", "r")
        jnl = explo_dir / "creative_space" / "journal"
        jnl.mkdir(parents=True)
        _write(jnl / "01_entry.md", "Entry", "2026-04-04", "r")

        block = exploration_reader.format_for_briefing()
        assert "2 explorations" in block
        assert "1 creative" in block
        assert "1 journal" in block

    def test_names_browse_and_search_commands(self, explo_dir):
        _write(explo_dir / "01_topic.md", "T", "2026-04-01", "r")
        block = exploration_reader.format_for_briefing()
        assert "divineos study" in block
        assert "divineos ask" in block

    def test_recent_cap(self, explo_dir):
        """When there are many entries, only the cap is listed."""
        for i in range(1, 11):
            _write(explo_dir / f"{i:02d}_topic.md", f"Topic {i:02d}", f"2026-04-{i:02d}", "r")
        block = exploration_reader.format_for_briefing(max_recent=3)
        # Latest three (10, 09, 08) should appear; earliest (01) should not
        assert "Topic 10" in block
        assert "Topic 09" in block
        assert "Topic 08" in block
        assert "Topic 01" not in block

    def test_newest_first(self, explo_dir):
        _write(explo_dir / "01_old.md", "Oldest", "2026-04-01", "r")
        _write(explo_dir / "05_newer.md", "Newer", "2026-04-05", "r")
        _write(explo_dir / "10_newest.md", "Newest", "2026-04-10", "r")
        block = exploration_reader.format_for_briefing()
        # Position of Newest should come before Oldest in the block
        assert block.index("Newest") < block.index("Oldest")

    def test_block_ends_with_newline(self, explo_dir):
        """Convention matches other briefing surfaces."""
        _write(explo_dir / "01_topic.md", "T", "2026-04-01", "r")
        block = exploration_reader.format_for_briefing()
        assert block.endswith("\n")
