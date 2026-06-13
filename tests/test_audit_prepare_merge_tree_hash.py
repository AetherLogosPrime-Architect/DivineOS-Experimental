"""Tests for `divineos audit prepare-merge` tree-hash emission.

Phase 2 of the gate-patch (2026-06-13): the emitted trailer should
include `tree-hash:<40-hex>` by default so the server-side CI gate
can verify substance-binding. Falls back to legacy form with a
deprecation notice when git is unreachable or --no-tree-hash is set.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from unittest.mock import patch

from click.testing import CliRunner

from divineos.cli import cli


@dataclass
class _FakeRound:
    round_id: str = "round-fake12345"
    focus: str = "test round"
    created_at: float = 0.0  # patched in fixture so age is within window


@dataclass
class _FakeFinding:
    actor: str = "user"
    review_stance: object = None


def _patches(round_id="round-fake12345"):
    """Common patches: round + findings + recency."""
    import time as _t

    return [
        patch(
            "divineos.core.watchmen.store.get_round",
            return_value=_FakeRound(round_id=round_id, created_at=_t.time() - 3600),
        ),
        patch(
            "divineos.core.watchmen.store.list_findings",
            return_value=[
                _FakeFinding(actor="user"),
                _FakeFinding(actor="aletheia"),
            ],
        ),
    ]


def test_prepare_merge_emits_tree_hash_by_default():
    """Default behavior: trailer includes tree-hash from HEAD."""
    fake_tree = "abc1234567890abcdef1234567890abcdef12345"
    with (
        patch(
            "divineos.core.watchmen.store.get_round",
            return_value=_FakeRound(created_at=__import__("time").time() - 3600),
        ),
        patch(
            "divineos.core.watchmen.store.list_findings",
            return_value=[_FakeFinding(actor="user"), _FakeFinding(actor="aletheia")],
        ),
        patch("subprocess.run") as run,
    ):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=fake_tree + "\n", stderr=""
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "prepare-merge", "round-fake12345"])

    assert result.exit_code == 0, result.output
    assert f"External-Review: round-fake12345 tree-hash:{fake_tree}" in result.output
    assert "Substance-bound" in result.output or "substance-bound" in result.output.lower()


def test_prepare_merge_no_tree_hash_flag_emits_legacy_form():
    """--no-tree-hash flag emits the legacy trailer form."""
    with (
        patch(
            "divineos.core.watchmen.store.get_round",
            return_value=_FakeRound(created_at=__import__("time").time() - 3600),
        ),
        patch(
            "divineos.core.watchmen.store.list_findings",
            return_value=[_FakeFinding(actor="user"), _FakeFinding(actor="aletheia")],
        ),
    ):
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "prepare-merge", "round-fake12345", "--no-tree-hash"])

    assert result.exit_code == 0, result.output
    assert "External-Review: round-fake12345" in result.output
    assert "tree-hash:" not in result.output


def test_prepare_merge_falls_back_when_git_unreachable():
    """If git fails, legacy form is emitted with a deprecation notice."""
    with (
        patch(
            "divineos.core.watchmen.store.get_round",
            return_value=_FakeRound(created_at=__import__("time").time() - 3600),
        ),
        patch(
            "divineos.core.watchmen.store.list_findings",
            return_value=[_FakeFinding(actor="user"), _FakeFinding(actor="aletheia")],
        ),
        patch("subprocess.run") as run,
    ):
        run.side_effect = FileNotFoundError("git not on PATH")
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "prepare-merge", "round-fake12345"])

    assert result.exit_code == 0, result.output
    assert "External-Review: round-fake12345" in result.output
    # Legacy form — no tree-hash suffix
    assert "tree-hash:" not in result.output
    # Deprecation notice surfaced to operator
    assert "LEGACY" in result.output or "DEPRECATED" in result.output
