"""Tests for the deletion-discipline gate (prereg-251b15df9461).

Two-sided by construction: destructive deletions must be CAUGHT; benign /
ephemeral operations must STAY SILENT (false-positive friction trains
route-around — the gate-misfire family). Plus the justification flow:
record clears the block, TTL expires it, hollow justifications are rejected.
"""

from __future__ import annotations

import pytest

from divineos.core import deletion_discipline as dd


@pytest.fixture(autouse=True)
def _isolate_justifications(tmp_path, monkeypatch):
    """Point the justification marker at a temp file per test."""
    monkeypatch.setattr(dd, "marker_path", lambda name: tmp_path / name)


class TestDestructiveDetection:
    DESTRUCTIVE = [
        "git push origin --delete old-branch",
        "git push origin :old-branch",
        "git branch -D feature-x",
        "git branch -d feature-x",
        "git branch --delete feature-x",
        "git rm src/divineos/core/foo.py",
        "rm -rf src/divineos/core",
        "rm -r tests/divineos",
        "rm -f src/divineos/important.py",
    ]

    def test_destructive_commands_flagged(self):
        for cmd in self.DESTRUCTIVE:
            ok, _ = dd.is_destructive_deletion(cmd)
            assert ok, f"failed to flag destructive: {cmd!r}"


class TestBenignStaysSilent:
    BENIGN = [
        "git push origin main",
        "git push -u origin feature-x",
        "git status",
        "git commit -m 'x'",
        "ls -la",
        "git branch --show-current",
        "rm -rf /tmp/scratch",
        "rm -rf __pycache__",
        "rm -rf build/",
        "rm -f some.pyc",
        "rm -rf .pytest_cache",
        "divineos briefing",
    ]

    def test_benign_commands_not_flagged(self):
        for cmd in self.BENIGN:
            ok, _ = dd.is_destructive_deletion(cmd)
            assert not ok, f"wrongly flagged benign: {cmd!r}"

    def test_benign_commands_not_blocked(self):
        for cmd in self.BENIGN:
            assert dd.block_reason(cmd) is None, f"wrongly blocked: {cmd!r}"


class TestQuotedContextNotTriggered:
    """Deletion verbs inside a commit message / echo / heredoc are TEXT, not
    invocations. The gate fired on its own commit message describing the
    patterns it detects (the context-blind-keyword misfire family) — these
    pin that it stays silent while real deletions still fire."""

    QUOTED_TEXT = [
        "git commit -m 'fix: describe git branch -D and git rm behaviour'",
        'git commit -m "add gate that blocks git push --delete"',
        'echo "to delete a branch use git branch -D name"',
        "git commit -m \"$(printf 'mentions git rm and rm -rf src/ in body')\"",
    ]

    def test_deletion_words_in_quotes_stay_silent(self):
        for cmd in self.QUOTED_TEXT:
            assert dd.block_reason(cmd) is None, f"wrongly blocked quoted text: {cmd!r}"

    def test_heredoc_commit_message_stays_silent(self):
        cmd = (
            "git commit -m \"$(cat <<'EOF'\n"
            "add: deletion gate\n\n"
            "detects git branch -D, git push --delete, git rm, rm -rf src/\n"
            'EOF\n)"'
        )
        assert dd.block_reason(cmd) is None

    def test_real_deletion_still_fires_alongside_quotes(self):
        # A real delete with an unrelated quoted arg must STILL fire.
        assert dd.block_reason("git branch -D feature-x  # 'keep this comment'") is not None


class TestJustificationFlow:
    def test_destructive_blocked_without_justification(self):
        assert dd.block_reason("git push origin --delete stale-branch") is not None

    def test_justification_clears_the_block(self):
        cmd = "git push origin --delete stale-branch"
        assert dd.block_reason(cmd) is not None
        dd.record_justification(
            target="stale-branch",
            why="merged via PR #99",
            investigated="diffed vs main; all files present",
            extracted="nothing unique; superseded",
        )
        assert dd.block_reason(cmd) is None

    def test_justification_is_per_target(self):
        dd.record_justification(target="branch-x", why="w", investigated="i", extracted="e")
        # Justifying branch-x does NOT clear deleting branch-y.
        assert dd.block_reason("git push origin --delete branch-y") is not None
        assert dd.block_reason("git push origin --delete branch-x") is None

    def test_ttl_expires_justification(self):
        cmd = "git branch -D temp"
        dd.record_justification(target="temp", why="w", investigated="i", extracted="e", now=1000.0)
        assert dd.block_reason(cmd, now=1000.0 + 1) is None  # fresh
        assert dd.block_reason(cmd, now=1000.0 + dd._TTL_SECONDS + 1) is not None  # stale

    def test_hollow_justification_rejected(self):
        for bad in (
            dict(target="x", why="", investigated="i", extracted="e"),
            dict(target="x", why="w", investigated="   ", extracted="e"),
            dict(target="x", why="w", investigated="i", extracted=""),
            dict(target="", why="w", investigated="i", extracted="e"),
        ):
            with pytest.raises(ValueError):
                dd.record_justification(**bad)
