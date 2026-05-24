"""Test the multiplex-as-default briefing and --legacy flag.

Multiplex became the default briefing output 2026-05-22. The old
single-window dashboard is available via --legacy for one release.
"""

from click.testing import CliRunner

from divineos.cli import cli


def test_default_briefing_renders_multiplex():
    """divineos briefing (no flags) should render multiplex panels."""
    runner = CliRunner()
    result = runner.invoke(cli, ["briefing"])
    assert result.exit_code == 0, f"non-zero exit: {result.output}"
    out = result.output
    assert "multiplex" in out.lower()
    assert "-" * 40 in out
    assert "More:" in out


def test_legacy_flag_renders_dashboard():
    """divineos briefing --legacy should render the old dashboard."""
    runner = CliRunner()
    result = runner.invoke(cli, ["briefing", "--legacy"])
    assert result.exit_code == 0, f"non-zero exit: {result.output}"
    out = result.output
    assert "BRIEFING" in out or "orientation" in out.lower()


def test_legacy_flag_in_help():
    """--help should mention --legacy."""
    runner = CliRunner()
    result = runner.invoke(cli, ["briefing", "--help"])
    assert result.exit_code == 0
    assert "--legacy" in result.output
