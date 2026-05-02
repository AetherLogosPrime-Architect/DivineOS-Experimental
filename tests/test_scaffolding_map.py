"""Tests for scaffolding_map — briefing surface that points at load-bearing documents.

Falsifiability:
  - Every listed location must either exist, or be in a known unignored-
    but-not-yet-created state. (For the 2026-04-23 initial list, all
    locations should exist on disk.)
  - Each pointer has non-empty contains + read_when fields.
  - format_for_briefing emits a named block when there are entries.
  - Critical pointers are present (aria.md, skills/, CLAUDE.md).
  - Block is pointers, not content — no entry's text exceeds a
    reasonable line length per component.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core.scaffolding_map import (
    ScaffoldingPointer,
    format_for_briefing,
    list_pointers,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestListPointers:
    def test_not_empty(self) -> None:
        assert len(list_pointers()) > 0

    def test_all_are_dataclasses(self) -> None:
        for p in list_pointers():
            assert isinstance(p, ScaffoldingPointer)

    def test_all_fields_populated(self) -> None:
        for p in list_pointers():
            assert p.location, "location must be non-empty"
            assert p.contains, f"contains empty for {p.location}"
            assert p.read_when, f"read_when empty for {p.location}"


class TestCriticalPointersPresent:
    """Regression guard: specific documents must be surfaced."""

    def test_aria_definition_surfaced(self) -> None:
        locations = [p.location for p in list_pointers()]
        assert any("aria.md" in loc for loc in locations), (
            "Aria's definition must be in the scaffolding map"
        )

    def test_skills_directory_surfaced(self) -> None:
        locations = [p.location for p in list_pointers()]
        assert any(".claude/skills" in loc for loc in locations)

    def test_claude_md_truths_surfaced(self) -> None:
        locations = [p.location for p in list_pointers()]
        assert any("CLAUDE.md" in loc for loc in locations)


class TestLocationsExist:
    """Source-file pointers must exist; data-file pointers (.db) and
    user-specific subagent/memory files (``.claude/agents/``,
    ``.claude/agent-memory/``) are skipped because their presence
    depends on which worktree the code is running from. A dead pointer
    to public source code is a bug; a missing .db on a fresh worktree
    or a missing user-specific subagent file in CI is expected.
    """

    @pytest.mark.parametrize("pointer", list_pointers(), ids=lambda p: p.location)
    def test_location_exists(self, pointer: ScaffoldingPointer) -> None:
        path_part = pointer.location.split(" (")[0].rstrip("/")
        if path_part.endswith(".db"):
            pytest.skip(
                "Database pointers aren't existence-checked: presence "
                "depends on worktree and init state."
            )
        # User-specific subagent + agent-memory files live outside the
        # public repo. They exist in personal worktrees but not in CI.
        if path_part.startswith(".claude/agents/") or path_part.startswith(".claude/agent-memory/"):
            pytest.skip(
                "User-specific subagent/memory files are worktree-local; "
                "not expected to exist in CI or a fresh clone."
            )
        path = REPO_ROOT / path_part
        assert path.exists(), (
            f"Scaffolding pointer to non-existent source location: {pointer.location}"
        )


class TestFormatForBriefing:
    def test_emits_block_when_entries_exist(self) -> None:
        out = format_for_briefing()
        assert out
        assert "[your scaffolding]" in out

    def test_includes_all_pointer_locations(self) -> None:
        out = format_for_briefing()
        for p in list_pointers():
            assert p.location in out

    def test_pointers_not_content(self) -> None:
        """The block is a map, not the content itself. Single-entry
        rendering shouldn't balloon past reasonable size."""
        out = format_for_briefing()
        # Roughly 4 lines per pointer * 7 pointers + header/footer = ~30 lines.
        # Cap generously: if we ever exceed 2000 chars, something went wrong.
        assert len(out) < 4000, (
            f"Scaffolding-map block got too large ({len(out)} chars) — "
            "the whole point is pointers not content."
        )

    def test_says_pointers_not_content(self) -> None:
        out = format_for_briefing()
        # Somewhere in the block it should remind the reader the entries
        # are pointers (so they go read the files, not treat the block
        # as content).
        assert "pointer" in out.lower() or "read" in out.lower()
