"""Tests for guardrail-aware PR opening (Andrew 2026-06-18 structural fix).

When `divineos prs --open-missing` would have opened a PR for a
guardrail-touching branch via `gh pr create --fill`, the resulting PR
body lacks the External-Review trailer (because the commit message
typically doesn't include one — commits are work-preservation, not
blocked over trailer absence per Aletheia Finding 78). The CI multi-
party-review check then correctly fails, burning a cycle.

This module's tests pin the structural fix: detect guardrail-touching
branches at open time and refuse `--fill`, naming the workflow instead.
"""

from __future__ import annotations

from divineos.cli.prs_commands import (
    _branch_touches_guardrail,
    _guardrail_paths,
)


class TestGuardrailPaths:
    """The helper that reads scripts/guardrail_files.txt."""

    def test_returns_set_of_paths(self) -> None:
        paths = _guardrail_paths()
        # The repo has a real guardrail_files.txt; this helper should
        # return at least one entry. Specific contents may evolve, so
        # we don't pin file names — just that the read works.
        assert isinstance(paths, set)
        # Sanity: known guardrail file is in the list.
        # (If the canonical kiln file gets renamed, update this.)
        assert any("foundational_truths" in p for p in paths)


class TestBranchTouchesGuardrail:
    """The diff-based detection of guardrail-file modification."""

    def test_returns_false_when_no_guardrails_defined(self, monkeypatch) -> None:
        """Fail-open: missing guardrail file → no detection, PR opens normally."""
        monkeypatch.setattr(
            "divineos.cli.prs_commands._guardrail_paths", lambda: set()
        )
        touches, files = _branch_touches_guardrail("any-branch")
        assert touches is False
        assert files == []

    def test_returns_false_when_git_diff_fails(self, monkeypatch) -> None:
        """Fail-open: git error → no detection, PR opens normally."""
        monkeypatch.setattr(
            "divineos.cli.prs_commands._guardrail_paths",
            lambda: {"src/divineos/foo.py"},
        )
        monkeypatch.setattr(
            "divineos.cli.prs_commands._run",
            lambda *a, **kw: (1, "", "git error"),
        )
        touches, files = _branch_touches_guardrail("any-branch")
        assert touches is False
        assert files == []

    def test_detects_guardrail_modification(self, monkeypatch) -> None:
        """When git diff lists a guardrail file as changed, touches=True."""
        monkeypatch.setattr(
            "divineos.cli.prs_commands._guardrail_paths",
            lambda: {"src/divineos/hooks/pre_tool_use_gate.py"},
        )
        monkeypatch.setattr(
            "divineos.cli.prs_commands._run",
            lambda *a, **kw: (
                0,
                "src/divineos/hooks/pre_tool_use_gate.py\nother/file.py\n",
                "",
            ),
        )
        touches, files = _branch_touches_guardrail("guardrail-touching-branch")
        assert touches is True
        assert files == ["src/divineos/hooks/pre_tool_use_gate.py"]

    def test_returns_false_when_no_guardrail_in_diff(self, monkeypatch) -> None:
        """Branch that doesn't touch guardrail → opens normally."""
        monkeypatch.setattr(
            "divineos.cli.prs_commands._guardrail_paths",
            lambda: {"src/divineos/hooks/pre_tool_use_gate.py"},
        )
        monkeypatch.setattr(
            "divineos.cli.prs_commands._run",
            lambda *a, **kw: (
                0,
                "tests/test_x.py\nsrc/divineos/core/foo.py\n",
                "",
            ),
        )
        touches, files = _branch_touches_guardrail("regular-branch")
        assert touches is False
        assert files == []

    def test_returns_multiple_guardrail_files_when_present(self, monkeypatch) -> None:
        """Multi-guardrail-file PR surfaces all of them for the workflow message."""
        monkeypatch.setattr(
            "divineos.cli.prs_commands._guardrail_paths",
            lambda: {
                "src/divineos/hooks/pre_tool_use_gate.py",
                "src/divineos/core/operating_loop_audit.py",
                "docs/foundational_truths.md",
            },
        )
        monkeypatch.setattr(
            "divineos.cli.prs_commands._run",
            lambda *a, **kw: (
                0,
                (
                    "src/divineos/hooks/pre_tool_use_gate.py\n"
                    "src/divineos/core/operating_loop_audit.py\n"
                    "tests/test_unrelated.py\n"
                ),
                "",
            ),
        )
        touches, files = _branch_touches_guardrail("multi-guardrail-branch")
        assert touches is True
        assert "src/divineos/hooks/pre_tool_use_gate.py" in files
        assert "src/divineos/core/operating_loop_audit.py" in files
        assert "tests/test_unrelated.py" not in files
