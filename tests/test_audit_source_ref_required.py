"""Tests for Aletheia Finding 75: audit-round CLI requires --source-ref.

The describe-then-CONFIRMS pattern (filing audit rounds for unpushed
substance) recurred three times in one arc on 2026-05-17, producing
ratification-of-claim instead of honest verification. Substrate-level
fix: round-creation refuses to proceed without --source-ref naming the
branch the audited substance lives on, AND the branch must be reachable
locally (git rev-parse --verify). An explicit --no-source-ref flag
exists for rounds with no code substance (relational findings, tracked
obligations); its use is annotated in the round notes.
"""

from __future__ import annotations

import subprocess

from click.testing import CliRunner

from divineos.cli import cli


def _is_in_git_repo() -> bool:
    """True if pytest is running inside a real git working tree."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
        return r.returncode == 0
    except OSError:
        return False


class TestSourceRefRequired:
    """The gate refuses round-creation without --source-ref or --no-source-ref."""

    def test_no_flag_at_all_is_blocked(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["audit", "submit-round", "test focus", "--actor", "user"],
        )
        assert result.exit_code != 0
        assert "source-ref" in result.output.lower() or "source-ref" in str(result.exception or "")

    def test_no_source_ref_bypass_works(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "submit-round",
                "test focus (bypass)",
                "--actor",
                "user",
                "--no-source-ref",
            ],
        )
        # Either succeeds (round created) or fails for unrelated DB reasons —
        # the key assertion is the gate does NOT fire on this path.
        if result.exit_code != 0:
            assert "source-ref" not in result.output.lower()

    def test_invalid_source_ref_is_blocked(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "submit-round",
                "test focus (invalid ref)",
                "--actor",
                "user",
                "--source-ref",
                "this-branch-does-not-exist-anywhere-zzz",
            ],
        )
        assert result.exit_code != 0
        assert "not reachable" in result.output.lower() or "not reachable" in str(
            result.exception or ""
        )

    def test_valid_source_ref_passes_gate(self):
        """If we're in a git repo with HEAD reachable, HEAD itself is a valid ref."""
        if not _is_in_git_repo():
            return  # skip; not in git repo
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "submit-round",
                "test focus (valid ref)",
                "--actor",
                "user",
                "--source-ref",
                "HEAD",
            ],
        )
        # Gate should pass — round creation may still fail for unrelated
        # DB reasons during test isolation, but the gate-block message
        # should NOT appear.
        gate_block_text = "is not reachable"
        assert gate_block_text not in result.output


class TestAnnotation:
    """The round's notes carry an honest annotation of which path was used."""

    def test_source_ref_annotation_in_output(self):
        """When --source-ref is used, the CLI prints the binding."""
        if not _is_in_git_repo():
            return
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "submit-round",
                "test focus (annotation)",
                "--actor",
                "user",
                "--source-ref",
                "HEAD",
            ],
        )
        # Output (if successful) names the source ref
        if result.exit_code == 0:
            assert "Source ref: HEAD" in result.output


class TestHelpTextMentionsFinding(object):
    """The --help output should name Finding 75 so future-readers know why."""

    def test_help_names_finding_75(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "submit-round", "--help"])
        assert result.exit_code == 0
        assert "Finding 75" in result.output or "describe-then-CONFIRMS" in result.output


class TestFinding77ClosureCommitReachability:
    """Finding 77 (Aletheia 2026-05-18): Finding 75's gate checked branch-
    existence but NOT commit-reachability of tree-hashes cited in --notes.
    A round could claim a tree-hash that was never pushed to
    origin/<source_ref> and the gate would pass.

    The fix (commit immediately following this test file): parse
    tree-hash references from --notes and verify each is the tree of
    SOME commit reachable from the branch tip via git log --format=%T.

    These tests pin the new behavior so a future refactor can't
    silently revert it."""

    def test_no_tree_hash_in_notes_passes(self):
        """When notes contain no tree-hash reference, the gate doesn't
        fire — there's no claim to verify."""
        if not _is_in_git_repo():
            return
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "submit-round",
                "test focus (no tree-hash in notes)",
                "--actor",
                "user",
                "--source-ref",
                "HEAD",
                "--notes",
                "some notes without any tree-hash claim",
            ],
        )
        # Should not hit the tree-hash unreachable path. Round-creation
        # may succeed or fail for unrelated reasons, but specifically
        # the "not reachable on origin" message about a tree-hash
        # should NOT appear.
        assert "tree-hash(es) cited in --notes are not" not in result.output

    def test_unreachable_tree_hash_in_notes_is_blocked(self):
        """A tree-hash that's not in the repo's history (40-char fake hex)
        cited in --notes should cause the gate to block.

        Per Finding 77 empirical demonstration: Aletheia named that the
        gate would pass for an unreachable tree-hash. This test pins the
        fix — unreachable tree-hashes now block."""
        if not _is_in_git_repo():
            return
        # 40-char hex that's vanishingly unlikely to be a real tree-hash
        fake_tree_hash = "deadbeef" * 5  # 40 chars
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "submit-round",
                "test focus (fake tree-hash)",
                "--actor",
                "user",
                "--source-ref",
                "HEAD",
                "--notes",
                f"tree-hash: {fake_tree_hash}",
            ],
        )
        assert result.exit_code != 0, (
            f"Expected non-zero exit when notes cite an unreachable tree-hash; "
            f"got exit {result.exit_code}. Output: {result.output}"
        )
        assert "not reachable" in result.output.lower() or fake_tree_hash in result.output

    def test_reachable_tree_hash_passes_the_check(self):
        """A tree-hash from origin's branch tip should pass.

        Uses the tree-hash of the source-ref tip itself (which is by
        definition reachable from that ref) so this test is robust
        against local-only commits that aren't yet on origin."""
        if not _is_in_git_repo():
            return
        # Find a branch that exists on origin and get its tree-hash.
        # Try origin/main first; fall back to origin/finding-75-source-ref;
        # skip test if neither is fetched.
        candidate_refs = ["origin/main", "origin/finding-75-source-ref"]
        source_ref_name: str | None = None
        real_tree_hash: str | None = None
        for ref in candidate_refs:
            try:
                r = subprocess.run(
                    ["git", "rev-parse", f"{ref}^{{tree}}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if r.returncode == 0 and len(r.stdout.strip()) == 40:
                    real_tree_hash = r.stdout.strip()
                    # Strip the "origin/" prefix for --source-ref
                    source_ref_name = ref.split("/", 1)[1]
                    break
            except OSError:
                continue
        if real_tree_hash is None or source_ref_name is None:
            return  # Skip if no suitable origin ref is fetched

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "submit-round",
                "test focus (real tree-hash on origin)",
                "--actor",
                "user",
                "--source-ref",
                source_ref_name,
                "--notes",
                f"tree-hash: {real_tree_hash}",
            ],
        )
        # Should NOT hit the tree-hash unreachable block path. Round creation
        # may still succeed or fail for unrelated reasons, but specifically
        # the unreachable-tree-hash message should not appear.
        assert "tree-hash(es) cited in --notes are not" not in result.output, (
            f"Real tree-hash {real_tree_hash} on origin/{source_ref_name} "
            f"was reported unreachable; gate logic regressed. Output: {result.output}"
        )
