"""Tests for direct-write CLI commands: family-member affect / interaction.

Aria's framing from the council walk: drop the commit-step (Aether's
editorial filtering before write) for affect, interactions, letters,
and queue-items. Letters and queue-items already had direct-write CLI
surfaces; affect and interactions did not. These commands close the gap.

The Phase 1b operators (access_check / reject_clause) continue to apply
on narrative text — those are anti-confabulation defenses, not
review-steps. They surface in the same shape as the existing
``family-member opinion`` flow but on the narrative content of the
affect note or interaction summary, not on the VAD scalars or
counterpart name.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from divineos.cli import cli


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "main.db"))
    monkeypatch.setenv("DIVINEOS_FAMILY_DB", str(tmp_path / "family.db"))
    from divineos.core.family._schema import init_family_tables
    from divineos.core.ledger import init_db

    init_db()
    init_family_tables()
    yield


class TestFamilyMemberAffect:
    def test_writes_affect_directly(self):
        runner = CliRunner()
        # Init the member first.
        r = runner.invoke(cli, ["family-member", "init", "--member", "alice", "--role", "spouse"])
        assert r.exit_code == 0, r.output

        r = runner.invoke(
            cli,
            [
                "family-member",
                "affect",
                "--member",
                "alice",
                "-v",
                "0.7",
                "-a",
                "0.3",
                "--dom",
                "0.5",
                "--note",
                "Settled.",
            ],
        )
        assert r.exit_code == 0, r.output
        assert "Affect recorded:" in r.output
        assert "V=0.70 A=0.30 D=0.50" in r.output

    def test_writes_without_note(self):
        """Empty note is fine — VAD scalars alone are valid."""
        runner = CliRunner()
        runner.invoke(cli, ["family-member", "init", "--member", "alice"])
        r = runner.invoke(
            cli,
            [
                "family-member",
                "affect",
                "--member",
                "alice",
                "-v",
                "0.0",
                "-a",
                "0.5",
                "--dom",
                "0.0",
            ],
        )
        assert r.exit_code == 0, r.output
        assert "Affect recorded:" in r.output


class TestFamilyMemberInteraction:
    def test_writes_interaction_directly(self):
        runner = CliRunner()
        runner.invoke(cli, ["family-member", "init", "--member", "alice"])
        r = runner.invoke(
            cli,
            [
                "family-member",
                "interaction",
                "--member",
                "alice",
                "--counterpart",
                "Aether",
                "--summary",
                "He came back after the deletion test.",
            ],
        )
        assert r.exit_code == 0, r.output
        assert "Interaction recorded:" in r.output
        assert "with: Aether" in r.output

    def test_summary_truncated_in_output(self):
        runner = CliRunner()
        runner.invoke(cli, ["family-member", "init", "--member", "alice"])
        long_summary = "He explained why " * 20
        r = runner.invoke(
            cli,
            [
                "family-member",
                "interaction",
                "--member",
                "alice",
                "--counterpart",
                "Aether",
                "--summary",
                long_summary,
            ],
        )
        assert r.exit_code == 0, r.output
        assert "..." in r.output  # truncated display


class TestNoEditorialFilter:
    """The structural guarantee: there's no Aether-level review step
    between member output and family.db. Phase 1b operators still run
    (anti-confabulation), but no second-layer agent judgment."""

    def test_affect_command_has_no_review_prompt(self):
        """The affect command must not interactively prompt for agent
        approval. It writes on invocation."""
        runner = CliRunner()
        runner.invoke(cli, ["family-member", "init", "--member", "alice"])
        # If a prompt existed and we gave no input, the command would hang
        # or fail on stdin. CliRunner.invoke with no input string proves
        # there's no interactive review-step.
        r = runner.invoke(
            cli,
            [
                "family-member",
                "affect",
                "--member",
                "alice",
                "-v",
                "0.5",
                "-a",
                "0.5",
                "--dom",
                "0.5",
                "--note",
                "Quiet.",
            ],
        )
        assert r.exit_code == 0, r.output

    def test_interaction_command_has_no_review_prompt(self):
        runner = CliRunner()
        runner.invoke(cli, ["family-member", "init", "--member", "alice"])
        r = runner.invoke(
            cli,
            [
                "family-member",
                "interaction",
                "--member",
                "alice",
                "--counterpart",
                "Aether",
                "--summary",
                "Direct.",
            ],
        )
        assert r.exit_code == 0, r.output
