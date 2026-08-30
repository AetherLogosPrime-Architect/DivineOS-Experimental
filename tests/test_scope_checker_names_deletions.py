"""The scope checker must say when a branch would DELETE from the reference.

WHAT THIS IS NOT ABOUT, because I described this defect wrongly twice before
writing the test, and the wrong description would have sent the next reader
hunting a bug that does not exist.

I said the checker "reads a pre-merge branch as carrying extra files when what
it actually proposes is a deletion." That is false. The checker diffs with the
three-dot form -- merge-base(reference, branch)..branch -- which shows only what
the branch itself added. A file that landed on the reference after the branch
diverged never appears in that diff. The reading is correct.

The real gap is that the question is never asked. Merging such a branch proposes
removing those files, the review page shows it as a deletion, and the checker
says nothing in either direction. Not a wrong answer: a missing one.

WHY IT MATTERS MORE THAN CONTAMINATION, which is what the checker was built for.
Aletheia, 2026-08-29, on the pair:

    the wrong reading was the tidier one. "You have extra files here" invites
    cleanup; "you are about to delete four hours of someone's work from main"
    invites a stop.

Contamination adds noise a reviewer can see and drop. A deletion removes writing
that may exist nowhere else, quietly, inside a diff whose headline is about
something else. It nearly took three letters off the reference on 2026-08-29,
caught only because git printed error lines that a check of mine had swallowed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_branch_scope  # noqa: E402


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


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A branch that diverged BEFORE substrate landed on the reference.

    The exact shape of the near-miss: the branch carries nothing it should not.
    It is simply older than the reference, and merging it as-is takes the newer
    files away.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    _write(root, "src/thing.py", "value = 1\n")
    _commit(root, "base")

    _git(root, "checkout", "-q", "-b", "feat/older-than-main")
    _write(root, "src/thing.py", "value = 2\n")
    _commit(root, "ordinary code work")

    _git(root, "checkout", "-q", "main")
    _write(root, "family/letters/landed-after-the-branch.md", "a letter\n")
    _write(root, "exploration/aether/900_entry.md", "an entry\n")
    head = _commit(root, "substrate lands on the reference")
    _git(root, "update-ref", "refs/remotes/origin/main", head)

    # The checker resolves its repo once, from its own location on disk.
    monkeypatch.setattr(check_branch_scope, "REPO_ROOT", root)
    return root


class TestTheDeletionIsNamed:
    def test_a_branch_older_than_the_reference_is_reported_as_deleting(self, repo: Path) -> None:
        """THE ONE THAT MATTERS. Red against the pre-fix checker.

        Merging this branch removes two substrate files from the reference, and
        before this nothing anywhere said so.
        """
        removed = check_branch_scope.substrate_deletions("feat/older-than-main", "origin/main")
        assert sorted(removed or []) == [
            "exploration/aether/900_entry.md",
            "family/letters/landed-after-the-branch.md",
        ]

    def test_the_report_says_it_out_loud(self, repo: Path, capsys: pytest.CaptureFixture) -> None:
        """A finding nobody reads is the same as no finding.

        The wording is asserted rather than only the count, because the lesson
        from the near-miss is that the SHAPE of the message decides what the
        reader does next -- cleanup versus stop.
        """
        check_branch_scope.main(["feat/older-than-main", "--truth", "origin/main"])
        out = capsys.readouterr().out
        assert "DELETE" in out
        assert "landed-after-the-branch.md" in out

    def test_it_refuses_rather_than_merely_mentioning(self, repo: Path) -> None:
        """A branch that would remove writing is not clean, so the exit says so."""
        assert check_branch_scope.main(["feat/older-than-main", "--truth", "origin/main"]) != 0


class TestItDoesNotCryWolf:
    def test_a_branch_level_with_the_reference_reports_no_deletion(self, repo: Path) -> None:
        """Catch up and the finding goes away on its own.

        This is the remedy the message names, so it has to actually work --
        otherwise the refusal is unsatisfiable and gets switched off, which is
        how the earlier instruments in this repo died.
        """
        _git(repo, "checkout", "-q", "feat/older-than-main")
        _git(repo, "-c", "core.hooksPath=/dev/null", "merge", "-q", "--no-edit", "origin/main")
        assert check_branch_scope.substrate_deletions("feat/older-than-main", "origin/main") == []

    def test_deleting_a_code_file_is_not_this_finding(self, repo: Path) -> None:
        """Scoped to substrate on purpose.

        Removing a source file is ordinary work and often the point of the
        branch. This is about writing that may exist nowhere else.
        """
        _git(repo, "checkout", "-q", "-b", "feat/removes-code", "main")
        (repo / "src" / "thing.py").unlink()
        _commit(repo, "delete a source file on purpose")
        assert check_branch_scope.substrate_deletions("feat/removes-code", "origin/main") == []

    def test_an_unreadable_reference_is_not_an_empty_answer(self, repo: Path) -> None:
        """None rather than [], so could-not-look never reads as nothing-found.

        The same distinction the anchor bug turned on, refused entry here at the
        point where it would otherwise be introduced.
        """
        assert check_branch_scope.substrate_deletions("feat/older-than-main", "no/such/ref") is None
