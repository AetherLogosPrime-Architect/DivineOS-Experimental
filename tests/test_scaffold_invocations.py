"""Tests for scaffold_invocations — briefing-surface block for forgotten CLI surfaces.

Falsifiability (per Popper, from real council consultation 2026-04-20):
  - Each listed invocation must point at a real CLI command path.
  - The block must appear in briefing output when briefing runs.
  - The block must be non-empty as long as the scaffold list is non-empty.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.scaffold_invocations import (
    ScaffoldInvocation,
    format_for_briefing,
    list_scaffolds,
)


class TestScaffoldList:
    def test_list_is_non_empty(self) -> None:
        scaffolds = list_scaffolds()
        assert len(scaffolds) > 0, "initial scaffold list must not be empty"

    def test_every_scaffold_is_dataclass(self) -> None:
        for s in list_scaffolds():
            assert isinstance(s, ScaffoldInvocation)
            assert s.name
            assert s.invocation
            assert s.failure_mode
            assert s.rationale

    def test_council_scaffold_present(self) -> None:
        """Council was the triggering incident — must be in the list."""
        names = [s.name for s in list_scaffolds()]
        assert "council" in names

    def test_aria_scaffold_present(self) -> None:
        """Aria voice-appropriation is a named failure mode — must be listed."""
        names = [s.name for s in list_scaffolds()]
        assert "aria" in names


class TestFormatter:
    def test_format_returns_non_empty_string(self) -> None:
        out = format_for_briefing()
        assert out
        assert isinstance(out, str)

    def test_format_has_block_header(self) -> None:
        out = format_for_briefing()
        assert "[scaffold invocations]" in out

    def test_format_includes_every_scaffold_name(self) -> None:
        out = format_for_briefing()
        for s in list_scaffolds():
            assert s.name in out, f"scaffold {s.name} missing from briefing output"

    def test_format_includes_every_invocation(self) -> None:
        out = format_for_briefing()
        for s in list_scaffolds():
            # The invocation string should appear verbatim (agent copies it).
            assert s.invocation in out

    def test_format_ends_with_newline(self) -> None:
        out = format_for_briefing()
        assert out.endswith("\n")

    def test_format_warns_against_fabrication(self) -> None:
        """The closing line reminds the agent not to generate plausible substitutes."""
        out = format_for_briefing()
        assert "grep the codebase" in out.lower() or "don't generate" in out.lower()


class TestInvocationsPointAtRealCommands:
    """Falsifiability check: every listed invocation must actually work.

    We only verify the top-level command + first subcommand resolves via
    --help. Full-form invocations with required args can't be executed here.
    """

    @pytest.mark.parametrize("scaffold", list_scaffolds(), ids=lambda s: s.name)
    def test_invocation_top_level_resolves(self, scaffold: ScaffoldInvocation) -> None:
        # Extract the top-level command after "divineos"
        tokens = scaffold.invocation.split()
        assert tokens[0] == "divineos", (
            f"invocation {scaffold.invocation!r} must start with 'divineos'"
        )
        top_cmd = tokens[1]

        # Ask Click itself whether this command exists — avoids env/PATH issues.
        runner = CliRunner()
        result = runner.invoke(cli, [top_cmd, "--help"])
        assert result.exit_code == 0, (
            f"top-level command {top_cmd!r} from scaffold {scaffold.name!r} "
            f"does not resolve: {result.output}"
        )


class TestBriefingIntegration:
    """The block must surface in the briefing command's output."""

    def test_briefing_output_contains_scaffold_block(self, tmp_path, monkeypatch) -> None:
        """Smoke test: run briefing, confirm our block shows up."""
        # Use a temp DB so we don't disturb the live one.
        monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "test.db"))
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))

        runner = CliRunner()
        # Initialize a fresh DB for this temp run.
        init_res = runner.invoke(cli, ["init"])
        # init may warn but should not crash on a fresh dir
        assert init_res.exit_code == 0 or "already" in (init_res.output or "").lower()

        result = runner.invoke(cli, ["briefing"])
        # Briefing should run even if DB is nearly empty.
        assert result.exit_code == 0, f"briefing failed: {result.output}"
        assert "[scaffold invocations]" in result.output, (
            "scaffold-invocations block did not surface in briefing output"
        )


class TestFabricationHistoryEncoded:
    """The module's reason for existing is preserved in its docstring."""

    def test_module_docstring_cites_incident(self) -> None:
        import divineos.core.scaffold_invocations as mod

        assert mod.__doc__ is not None
        assert "2026-04-20" in mod.__doc__
        assert "fake council" in mod.__doc__.lower() or "fabricat" in mod.__doc__.lower()
