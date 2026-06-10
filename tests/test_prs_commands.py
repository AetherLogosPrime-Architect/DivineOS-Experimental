"""Tests for `divineos prs` — the PR-opener helper.

Andrew 2026-06-09: tonight 4 branches were pushed without `gh pr create`
run, and the gap was invisible. This command surfaces local branches
with a remote counterpart that don't have an open PR.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from divineos.cli import cli
from divineos.cli import prs_commands as prs


def _fake_run_factory(responses: dict[tuple[str, ...], tuple[int, str, str]]):
    """Build a fake _run that dispatches by exact argv tuple."""

    def fake(args: list[str], timeout: float = 10.0):
        return responses.get(tuple(args), (1, "", "unknown"))

    return fake


class TestFindBranchesWithoutPrs:
    def test_returns_empty_when_no_local_branches(self, monkeypatch):
        responses = {
            ("git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"): (
                0,
                "",
                "",
            ),
        }
        monkeypatch.setattr(prs, "_run", _fake_run_factory(responses))
        assert prs.find_branches_without_prs() == []

    def test_excludes_main_branch(self, monkeypatch):
        responses = {
            ("git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"): (
                0,
                "main\nfeat/a\n",
                "",
            ),
            ("git", "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/"): (
                0,
                "origin/main\norigin/feat/a\n",
                "",
            ),
            (
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--json",
                "headRefName",
                "--limit",
                "100",
            ): (0, "[]", ""),
        }
        monkeypatch.setattr(prs, "_run", _fake_run_factory(responses))
        result = prs.find_branches_without_prs()
        # Local main has no PR but is skipped; feat/a is surfaced.
        assert result == ["feat/a"]

    def test_excludes_branches_with_open_prs(self, monkeypatch):
        responses = {
            ("git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"): (
                0,
                "feat/a\nfeat/b\nfeat/c\n",
                "",
            ),
            ("git", "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/"): (
                0,
                "origin/feat/a\norigin/feat/b\norigin/feat/c\n",
                "",
            ),
            (
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--json",
                "headRefName",
                "--limit",
                "100",
            ): (
                0,
                json.dumps([{"headRefName": "feat/a"}, {"headRefName": "feat/b"}]),
                "",
            ),
        }
        monkeypatch.setattr(prs, "_run", _fake_run_factory(responses))
        assert prs.find_branches_without_prs() == ["feat/c"]

    def test_excludes_branches_without_remote(self, monkeypatch):
        """A local-only branch can't have a PR open against it — filter early."""
        responses = {
            ("git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"): (
                0,
                "feat/a\nfeat/local-only\n",
                "",
            ),
            ("git", "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/"): (
                0,
                "origin/feat/a\n",
                "",
            ),
            (
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--json",
                "headRefName",
                "--limit",
                "100",
            ): (0, "[]", ""),
        }
        monkeypatch.setattr(prs, "_run", _fake_run_factory(responses))
        assert prs.find_branches_without_prs() == ["feat/a"]


class TestPrsCommand:
    def test_command_silent_when_nothing_missing(self, monkeypatch):
        with patch.object(prs, "find_branches_without_prs", return_value=[]):
            result = CliRunner().invoke(cli, ["prs"])
        assert result.exit_code == 0
        assert "All local branches" in result.output

    def test_command_lists_missing_without_opening(self, monkeypatch):
        with patch.object(prs, "find_branches_without_prs", return_value=["feat/x", "feat/y"]):
            result = CliRunner().invoke(cli, ["prs"])
        assert result.exit_code == 0
        assert "2 branch(es) need a PR" in result.output
        assert "feat/x" in result.output
        assert "feat/y" in result.output
        # No gh pr create call because --open-missing not passed.
        assert "Opening PRs" not in result.output

    def test_command_open_missing_invokes_gh_pr_create(self, monkeypatch):
        calls: list[list[str]] = []

        def fake_run(args, timeout=10.0):
            calls.append(args)
            if args[:3] == ["gh", "pr", "create"]:
                return (
                    0,
                    "https://github.com/owner/repo/pull/999\n",
                    "",
                )
            return (1, "", "unexpected")

        monkeypatch.setattr(prs, "_run", fake_run)
        with patch.object(prs, "find_branches_without_prs", return_value=["feat/x"]):
            result = CliRunner().invoke(cli, ["prs", "--open-missing"])
        assert result.exit_code == 0
        assert any(c[:3] == ["gh", "pr", "create"] for c in calls)
        assert "1 opened" in result.output
