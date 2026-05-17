"""Test the --multiplex flag integration for divineos briefing.

Per prereg-ebee9082d201: multiplex briefing is opt-in MVP via flag; default
briefing flow unaffected. This test verifies the CLI flag wires up correctly
to the panel system via in-process click.testing.CliRunner.
"""

from click.testing import CliRunner

from divineos.cli import cli


def test_multiplex_flag_renders_panels():
    """divineos briefing --multiplex should print panel content with separators."""
    runner = CliRunner()
    result = runner.invoke(cli, ["briefing", "--multiplex"])
    assert result.exit_code == 0, f"non-zero exit: {result.output}"
    out = result.output
    assert "[multiplex] context:" in out
    assert "-" * 40 in out
    assert "More:" in out


def test_multiplex_flag_does_not_break_help():
    """--help should still work and mention --multiplex."""
    runner = CliRunner()
    result = runner.invoke(cli, ["briefing", "--help"])
    assert result.exit_code == 0
    assert "--multiplex" in result.output
