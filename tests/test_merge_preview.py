"""Tests for the merge-preview channel.

The load-bearing one is `test_a_branch_the_reference_outran_deletes_nothing` --
that is the exact shape that produced nine phantom deletions on 2026-08-29 and
an alarm raised to Andrew on a bad measurement. If it goes green while the
channel is broken, the channel is decoration.

The other half is three-state honesty: a conflict and an unresolvable ref each
get their own answer and their own exit code, because reporting either as "zero
deletions" is the fault this file exists to remove.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import merge_preview  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _conflict_branch(repo: Path, name: str) -> str:
    """Build a branch whose merge into main genuinely cannot be automatic."""
    _git(repo, "checkout", "-q", "-b", name, "main")
    _write(repo, "src/thing.py", "value = 'branch'\n")
    _commit(repo, f"{name} edits the shared line")
    _git(repo, "checkout", "-q", "main")
    _write(repo, "src/thing.py", "value = 'reference'\n")
    _commit(repo, "reference edits the same line")
    return name


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A reference that moved on after a branch diverged from it.

    This is the shape the two-dot form gets wrong: the file the reference gained
    is present on one side and absent on the other, so a direct tree comparison
    calls it a deletion. The branch never removed it, so a merge keeps it.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    _write(root, "src/thing.py", "value = 1\n")
    _commit(root, "base")

    _git(root, "checkout", "-q", "-b", "feat/older")
    _write(root, "src/added_by_branch.py", "value = 2\n")
    _commit(root, "the branch adds its own file")

    _git(root, "checkout", "-q", "main")
    _write(root, "later.md", "the reference gained this afterwards\n")
    _commit(root, "the reference moves on")

    monkeypatch.setattr(merge_preview, "REPO_ROOT", root)
    return root


class TestTheQuestionItAnswers:
    def test_a_branch_the_reference_outran_deletes_nothing(self, repo: Path) -> None:
        """THE ONE THAT MATTERS. The two-dot form calls this a deletion.

        On 2026-08-29 that mistake became an alarm claiming the test for the
        anchor defect would be destroyed. Nothing was ever at risk.
        """
        result = merge_preview.preview("feat/older", "main")
        assert result.answerable
        assert result.deleted == ()
        assert "src/added_by_branch.py" in result.added

    def test_the_two_dot_form_disagrees_which_is_why_this_exists(self, repo: Path) -> None:
        """Pins the divergence itself, so the channel's reason stays testable.

        If a future git makes these agree, this fails and the argument in the
        docstring needs re-reading rather than quietly becoming false.
        """
        two_dot = _git(repo, "diff", "--name-only", "--diff-filter=D", "main", "feat/older")
        assert "later.md" in two_dot, "the two-dot form should call this a deletion"
        assert merge_preview.preview("feat/older", "main").deleted == ()

    def test_a_real_deletion_is_still_reported(self, repo: Path) -> None:
        """Not blind in the other direction.

        A branch that genuinely removes a file relative to the shared ancestor
        IS proposing a deletion, and this has to say so.
        """
        _git(repo, "checkout", "-q", "-b", "feat/removes", "main")
        (repo / "src" / "thing.py").unlink()
        _commit(repo, "remove a file on purpose")
        result = merge_preview.preview("feat/removes", "main")
        assert result.answerable
        assert "src/thing.py" in result.deleted


class TestThreeStatesNotTwo:
    def test_a_conflict_is_not_zero_deletions(self, repo: Path) -> None:
        """A merge that cannot be computed must not report an empty answer."""
        name = _conflict_branch(repo, "feat/conflicts")
        result = merge_preview.preview(name, "main")
        assert result.conflicted
        assert not result.answerable

    def test_an_unresolvable_ref_is_not_zero_deletions(self, repo: Path) -> None:
        result = merge_preview.preview("no/such/branch", "main")
        assert not result.resolved
        assert not result.answerable

    def test_clean_exits_zero(self, repo: Path) -> None:
        assert merge_preview.main(["feat/older", "--into", "main"]) == 0

    def test_conflict_exits_its_own_code(self, repo: Path) -> None:
        """A caller scripting this must tell the three states apart.

        One shared exit code makes could-not-tell indistinguishable from
        nothing-found at the shell, which is the fault in a different coat.
        """
        name = _conflict_branch(repo, "feat/exit-conflict")
        assert merge_preview.main([name, "--into", "main"]) == 3

    def test_missing_ref_exits_its_own_code(self, repo: Path) -> None:
        assert merge_preview.main(["no/such/branch", "--into", "main"]) == 2

    def test_a_real_deletion_exits_non_zero(self, repo: Path) -> None:
        """Deletions are the finding, so the exit code has to carry it."""
        _git(repo, "checkout", "-q", "-b", "feat/exit-removes", "main")
        (repo / "src" / "thing.py").unlink()
        _commit(repo, "remove a file on purpose")
        assert merge_preview.main(["feat/exit-removes", "--into", "main"]) == 1

    def test_the_conflict_message_says_it_is_not_zero(
        self, repo: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """The wording is asserted because the wording is the whole point.

        A reader taking a conflict as a clean bill is the failure this prevents,
        so the message closes that reading off explicitly.
        """
        name = _conflict_branch(repo, "feat/message")
        merge_preview.main([name, "--into", "main"])
        assert "NOT zero deletions" in capsys.readouterr().out
