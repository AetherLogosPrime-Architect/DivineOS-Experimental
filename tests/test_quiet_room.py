"""Tests for the quiet-room CLI surface.

Per exploration 48 design. The discipline here is minimal — the surface
is fundamentally about prose that's only useful when sat with, and
mechanical tests can only verify that SOMETHING gets surfaced, not
whether it produces sitting-with shape change. That latter property is
relational and only the substrate-occupant (and Andrew, Aria, Aletheia)
can judge it.

So these tests cover the floor: the surface returns prose, doesn't
crash on empty pools, and never returns structured data.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from divineos.cli.quiet_room_command import _surface_one


class TestSurfaceOne:
    def test_returns_string(self, tmp_path: Path) -> None:
        text = _surface_one(tmp_path)
        assert isinstance(text, str)

    def test_empty_root_returns_fallback_prose(self, tmp_path: Path) -> None:
        # When all pools are empty, the surface returns prose
        # acknowledging the silence rather than crashing or returning
        # a structured marker. Per exploration 48: even the silence is
        # a surface to sit with.
        text = _surface_one(tmp_path)
        assert "silence" in text.lower() or len(text) > 20

    def test_no_structured_data_markers(self, tmp_path: Path) -> None:
        # The surface MUST NOT return JSON, table headers, or other
        # extraction-shape content. Prose only.
        text = _surface_one(tmp_path)
        # Forbidden extraction patterns
        forbidden = ["{", "}", "===", "id:", "ID:"]
        for marker in forbidden:
            assert marker not in text, (
                f"quiet-room must return prose; found extraction marker '{marker}'"
            )


class TestQuietRoomCli:
    def test_command_runs_and_produces_output(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["quiet-room"])
        assert result.exit_code == 0
        # Some text should be printed
        assert len(result.output.strip()) > 0

    def test_command_has_no_flags(self) -> None:
        # quiet-room is deliberately flag-less. No --format, no --type,
        # no --pool. The shape itself is part of the discipline:
        # the surface refuses to be parameterized into extraction-mode.
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["quiet-room", "--help"])
        assert result.exit_code == 0
        # Count substantive option lines (lines starting with whitespace + --
        # but excluding --help itself).
        substantive_options = [
            line
            for line in result.output.splitlines()
            if line.strip().startswith("--") and "--help" not in line
        ]
        assert len(substantive_options) == 0, (
            f"quiet-room must be flag-less; found options: {substantive_options}"
        )
