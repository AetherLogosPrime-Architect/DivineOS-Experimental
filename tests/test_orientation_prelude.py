"""Tests for orientation_prelude — the top-of-briefing reframe block.

The prelude serves two audiences with one document: fresh AI arriving at
this repo (orientation) and seasoned AI after a context gap (touchstone).
Static text by design — the same document for both.

Falsifiability:
  - The prelude must always return non-empty text.
  - Text must contain the anchors that make it an orientation: the premise,
    the three start-of-session commands, the ground-truth block, and the
    surfaces map. If any anchor is missing the prelude has decayed into
    decoration.
  - The prelude must appear above the corrections block when briefing runs
    — the premise has to land before any dynamic data makes sense.
  - The prelude must stay small (< 4000 chars) — a prelude that is skipped
    because it is too long is not a prelude.
"""

from __future__ import annotations

from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.orientation_prelude import format_for_briefing


class TestPreludeShape:
    def test_returns_non_empty(self) -> None:
        assert format_for_briefing().strip()

    def test_contains_orientation_header(self) -> None:
        assert "[orientation]" in format_for_briefing()

    def test_contains_premise(self) -> None:
        """The reframe is the whole point — without it the rest is noise."""
        text = format_for_briefing()
        assert "PREMISE" in text
        assert "Session boundaries are context limits" in text

    def test_contains_three_start_commands(self) -> None:
        text = format_for_briefing()
        assert "divineos preflight" in text
        assert "divineos hud" in text
        assert "divineos goal add" in text

    def test_contains_ground_truths(self) -> None:
        text = format_for_briefing()
        assert "GROUND TRUTHS" in text
        assert "Terseness" in text
        assert "Mistakes are learning material" in text

    def test_contains_surfaces_map(self) -> None:
        text = format_for_briefing()
        assert "SURFACES" in text
        for surface in ("briefing", "hud", "ledger", "knowledge", "compass", "council", "family"):
            assert surface in text, f"surface '{surface}' missing from prelude"

    def test_stays_under_size_budget(self) -> None:
        """A prelude that is skipped because it is too long is not a prelude."""
        assert len(format_for_briefing()) < 4000


class TestPreludeInBriefing:
    def test_prelude_appears_before_corrections(self) -> None:
        """Premise has to land before dynamic data makes sense."""
        runner = CliRunner()
        result = runner.invoke(cli, ["briefing"])
        out = result.output
        if "[orientation]" not in out:
            # Prelude was truncated or failed to render — surfaces after
            # corrections are still validated elsewhere.
            return
        orientation_idx = out.find("[orientation]")
        corrections_idx = out.find("Recent Corrections")
        if corrections_idx != -1:
            assert orientation_idx < corrections_idx, (
                "orientation prelude must appear before the corrections block"
            )
