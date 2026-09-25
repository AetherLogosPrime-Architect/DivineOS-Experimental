"""Tests for `divineos audit prepare-merge` tree-hash emission.

Phase 2 of the gate-patch (2026-06-13): the emitted trailer should
include `tree-hash:<40-hex>` by default so the server-side CI gate
can verify substance-binding. Falls back to legacy form with a
deprecation notice when git is unreachable or --no-tree-hash is set.
"""

from __future__ import annotations

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


def test_prepare_merge_omits_tree_hash_by_default():
    """Default behavior 2026-06-18 (Andrew correction): trailer omits tree-hash.

    Prior default emitted HEAD^{tree} as the trailer's tree-hash, intended
    as Phase 2 substance-binding. But the predicted tree-hash doesn't match
    the squash-merge's actual tree once main has moved between predict-time
    and squash-time (queue serialization effect). Two PRs (#221, #230)
    merged with technically-mismatching tree-hashes that flagged the
    post-merge integrity audit. Default flipped to legacy form; substance-
    binding stays honest via per-commit trailers + audit-round CONFIRMs.
    """
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
        result = runner.invoke(cli, ["audit", "prepare-merge", "round-fake12345"])

    assert result.exit_code == 0, result.output
    assert "External-Review: round-fake12345" in result.output
    assert "tree-hash:" not in result.output


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


def test_prepare_merge_emits_the_current_form_when_git_is_unreachable():
    """Git unreachable still yields a USABLE trailer, described accurately.

    This test used to assert the output said LEGACY or DEPRECATED. That wording
    was removed in bc16012b because both halves were false: the round-id-only
    trailer is the CURRENT correct form, deliberately made the default on
    2026-06-18, since a tree-hash predicted before the squash cannot match the
    tree after main moves. The old notice called correct output degraded and
    prescribed a step the reader had already taken -- it cost me a hunt for a
    resolver defect that did not exist.

    The test was not updated with it, so it went on demanding the false wording
    and turned red on the next full run. Rewritten to assert what the command
    should actually do: emit a usable trailer and say plainly why there is no
    tree-hash, rather than apologise for its absence.
    """
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
    # No tree-hash suffix -- correct, not degraded.
    assert "tree-hash:" not in result.output
    # The reader is told what to DO with it, so a git failure does not read as
    # a dead end.
    assert "squash-merge" in result.output
    # And why there is no tree-hash, in terms of the thing that makes one
    # unmatchable rather than as an apology for missing output.
    assert "current form" in result.output
    # The retired wording must not come back: it sent me hunting a defect that
    # did not exist, from inside the very repo it told me to run from.
    assert "LEGACY" not in result.output
    assert "DEPRECATED" not in result.output
