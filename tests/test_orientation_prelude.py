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

import pytest
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
        assert "My memory persists" in text
        assert "context window doesn't" in text

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
    """Found by the cut-away sweep, 2026-10-07. The old single test returned silently when the
    prelude was missing and compared against a heading, "Recent Corrections", that the
    multiplex briefing no longer prints, so its ordering claim was never checked. It is now
    two tests: that the prelude is in the briefing (checked), and the ordering claim as an
    expected failure, because measured today the prelude is NOT first."""

    def test_the_prelude_is_in_the_briefing(self) -> None:
        out = CliRunner().invoke(cli, ["briefing"]).output
        assert "[orientation]" in out, out[:400]

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "measured 2026-10-07: the prelude prints after the multiplex panels, not before "
            "them. The module's own falsifiability line says the premise should land first. "
            "Either the briefing order or this claim is wrong; the owner decides. If the order "
            "is fixed this turns into an unexpected pass and fails, which forces the removal "
            "of this marker."
        ),
    )
    def test_the_prelude_lands_before_the_panels(self) -> None:
        out = CliRunner().invoke(cli, ["briefing"]).output
        header = out.find("=== BRIEFING (multiplex")
        assert header != -1, "the multiplex briefing header is missing"
        first_panel = out.find("\n\n", header) + 2
        assert out.find("[orientation]") < first_panel
