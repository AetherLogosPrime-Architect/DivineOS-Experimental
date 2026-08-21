"""Tests for `divineos label-fire` (register item O).

The load-bearing one is the reachability test: the whole point of this command
is that the false-positive path must be reachable through the same bypass
channel as every other gate remedy. If it drops out of the bypass list, the
toll silently comes back.
"""

from __future__ import annotations

import click
from click.testing import CliRunner

from divineos.cli import label_fire_commands as lfc


def _invoke(args):
    grp = click.Group()
    lfc.register(grp)
    return CliRunner().invoke(grp, args)


def test_command_is_on_the_hook_bypass_list():
    """Register item O: the remedy must not be tolled by the gates it disputes.

    A bypass entry that silently stops matching restores the exact problem
    this command was built to remove, and nothing else would notice.
    """
    from divineos.hooks.pre_tool_use_gate import _load_bypass_subcommands

    assert "label-fire" in _load_bypass_subcommands()


def test_labeller_script_resolves():
    """The prescribed remedy must exist — same class as the corrections-mirror
    bug where a printed command pointed at nothing."""
    assert lfc._script_path().exists(), f"labeller missing at {lfc._script_path()}"


def test_missing_labeller_says_nothing_was_recorded(monkeypatch, tmp_path):
    """The third word: a missing labeller is not a successful label."""
    monkeypatch.setattr(lfc, "_script_path", lambda: tmp_path / "gone.py")
    result = _invoke(["label-fire", "--reason", "x" * 50])
    assert result.exit_code != 0
    assert "CANNOT LABEL" in result.output
    assert "not 'label filed'" in result.output


def test_reason_is_required():
    """No leniency added over the script: a label still costs a real reason."""
    result = _invoke(["label-fire"])
    assert result.exit_code != 0
    assert "reason" in result.output.lower()
