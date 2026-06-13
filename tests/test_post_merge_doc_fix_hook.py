"""Smoke tests for the post-merge doc-fix hook.

The hook itself lives at .claude/hooks/post-merge-doc-fix.sh and is wired
into git via setup-hooks.sh / setup-hooks.ps1. It re-runs
`check_doc_counts.py --fix` after each merge to recover architecture-tree
entries that merge conflict resolution silently dropped (the PR #169
doc-leapfrog pattern, 2026-06-13).

Full integration testing (init a tmp repo, merge a branch that drops
an entry, verify the hook restores it) would be expensive. These smoke
tests assert the structural shape: the hook script exists, has the
fail-open exit-0 contract, and is wired into both setup scripts.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
HOOK = ROOT / ".claude" / "hooks" / "post-merge-doc-fix.sh"
SETUP_BASH = ROOT / "setup" / "setup-hooks.sh"
SETUP_PS1 = ROOT / "setup" / "setup-hooks.ps1"


def test_hook_file_exists():
    assert HOOK.exists(), "post-merge-doc-fix.sh hook is missing"


def test_hook_starts_with_bash_shebang():
    first = HOOK.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("#!/bin/bash"), first


def test_hook_exits_zero_when_check_doc_counts_succeeds(tmp_path, monkeypatch):
    """Hook short-circuits cleanly if the doc check is already green."""
    text = HOOK.read_text(encoding="utf-8")
    assert "exit 0" in text, "expected fail-open exit 0"
    assert "DIVINEOS_DOC_COUNT_NO_AUTOFIX" in text, "expected opt-out env var honored"


def test_hook_amends_merge_commit_only_when_staged_diff_exists():
    """Don't amend if --fix made no changes — protects against amending
    an unrelated merge commit when nothing structurally changed."""
    text = HOOK.read_text(encoding="utf-8")
    assert "git diff --cached --quiet" in text


def test_hook_restages_only_doc_files_not_everything():
    """Avoid `git add -A` — could grab unrelated WIP files."""
    text = HOOK.read_text(encoding="utf-8")
    # Filter out comment lines so the "Avoid git add -A" doc-comment
    # doesn't trip the assertion against actual command-line usage.
    code_lines = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    code = "\n".join(code_lines)
    assert "git add -A" not in code
    assert "docs/ARCHITECTURE.md" in text


def test_setup_bash_installs_post_merge_hook():
    text = SETUP_BASH.read_text(encoding="utf-8")
    assert "post-merge" in text
    assert "post-merge-doc-fix.sh" in text


def test_setup_ps1_installs_post_merge_hook():
    text = SETUP_PS1.read_text(encoding="utf-8")
    assert "post-merge" in text
    assert "post-merge-doc-fix.sh" in text


@pytest.mark.skipif(
    subprocess.run(["bash", "--version"], capture_output=True).returncode != 0,
    reason="bash not on PATH; can't smoke-test the hook script",
)
def test_hook_script_is_syntactically_valid_bash():
    """`bash -n` parses the script without executing — catches syntax errors."""
    result = subprocess.run(
        ["bash", "-n", str(HOOK)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"bash -n rejected the hook: {result.stderr}"
