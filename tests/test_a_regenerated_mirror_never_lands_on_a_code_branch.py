"""A regenerated mirror never lands on a code branch at a checkpoint.

Measured 2026-09-23, after Andrew asked why two findings I had filed as serious
had no urgency behind them. Three local-only commits on two code branches
(fix/the-index-reads-the-home-it-was-given, fix/the-runway-meter-reads-the-real-
trigger) each carried the same eleven docs/archives/*.md files, thousands of
lines, under the subject "auto-commit (pre-extract): work in progress". A plain
push of either would have put unreviewed substrate into a code PR that Aletheia
had already confirmed.

THE MECHANISM, read rather than guessed. docs/archives/ IS a declared substrate
prefix, and the checkpoint DOES route through auto_commit_substrate. The files
went to HEAD anyway because of the ALREADY-TRACKED exception: a declared
substrate path that is tracked on the current branch is committed here, since
retargeting it would leave the tree permanently dirty. That exception was written
for letters an old sweep had put onto a branch -- branch-local history. But all
twelve archive files are tracked on MAIN, so every code branch inherits them as
already-tracked, and every checkpoint takes the exception.

THE REPAIR, and why it is safe only for this class. The archives are pure
functions of the canonical SQLite (core/archive_export.py regenerates them), and
nothing reads them back from the working tree. So a regenerated mirror can be
committed to the substrate branch and then have its working copy RESTORED to the
checked-out branch's version: nothing is lost, the new bytes are on the
substrate branch, and the tree goes clean. A letter is not a mirror -- its
working copy may be the only one -- so letters keep the old behaviour.

These run against real repositories. The first one failed before the fix.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.auto_commit import auto_commit_substrate

ARCHIVE = "docs/archives/claims.md"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """main tracks an archive; a substrate branch and a code branch exist.

    Exactly the house's shape: the archive is committed on main, so the code
    branch inherits it as tracked. No external channel is needed -- the
    archive is regenerated in place, which is how it actually arrives.
    """
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-b", "main")
    _git(r, "config", "user.email", "test@example.com")
    _git(r, "config", "user.name", "Test")
    (r / "README.md").write_text("seed\n", encoding="utf-8")
    (r / "docs" / "archives").mkdir(parents=True)
    (r / ARCHIVE).write_text("claims v1\n", encoding="utf-8")
    (r / "tracked_code.py").write_text("x = 1\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-m", "seed")

    _git(r, "branch", "substrate/aether")
    _git(r, "config", "divineos.substrate-branch", "substrate/aether")
    _git(r, "checkout", "-b", "fix/some-code-change")
    return r


def _files_changed_by_head_since(repo: Path, rev: str) -> set[str]:
    out = _git(repo, "diff", "--name-only", rev, "HEAD")
    return {line for line in out.splitlines() if line}


class TestTheDefect:
    def test_a_regenerated_archive_does_not_land_on_the_code_branch(self, repo):
        before = _git(repo, "rev-parse", "HEAD")
        (repo / ARCHIVE).write_text("claims v2, regenerated from the DB\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        assert ARCHIVE not in _files_changed_by_head_since(repo, before), (
            "the regenerated archive was committed onto the code branch -- the "
            "exact contamination measured on two branches on 2026-09-23"
        )

    def test_the_new_bytes_reach_the_substrate_branch(self, repo):
        (repo / ARCHIVE).write_text("claims v2, regenerated from the DB\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        assert (
            _git(repo, "show", f"substrate/aether:{ARCHIVE}")
            == "claims v2, regenerated from the DB"
        )

    def test_the_tree_is_left_clean(self, repo):
        # Without the restore, the retarget would leave the archive modified on
        # disk forever -- the reason the already-tracked exception exists.
        (repo / ARCHIVE).write_text("claims v2, regenerated from the DB\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        assert _git(repo, "status", "--porcelain", "--", ARCHIVE) == ""


class TestItDoesNotReachTooFar:
    def test_tracked_code_is_still_saved_on_the_code_branch(self, repo):
        # The checkpoint's other promise: the occupant's unfinished work is
        # never lost. A tracked NON-mirror file must still be committed here.
        before = _git(repo, "rev-parse", "HEAD")
        (repo / "tracked_code.py").write_text("x = 2  # half done\n", encoding="utf-8")
        (repo / ARCHIVE).write_text("claims v2\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        changed = _files_changed_by_head_since(repo, before)
        assert "tracked_code.py" in changed
        assert ARCHIVE not in changed

    def test_undeclared_substrate_branch_leaves_the_archive_dirty_not_committed(self, repo):
        # Refuse, never fall back to HEAD. The archive is regenerable from the
        # DB, so leaving it modified on disk loses nothing; committing it here
        # is the defect.
        _git(repo, "config", "--unset", "divineos.substrate-branch")
        before = _git(repo, "rev-parse", "HEAD")
        (repo / ARCHIVE).write_text("claims v2\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        assert ARCHIVE not in _files_changed_by_head_since(repo, before)
        assert (repo / ARCHIVE).read_text(encoding="utf-8") == "claims v2\n"

    def test_the_restorable_list_cannot_grow_without_this_test_changing(self):
        # Council walk-dbd9b44bfad3, Beer lens: the tuple is the ONLY thing
        # between the restore and a letter's only copy, and nothing checked
        # what went into it. The restore overwrites a working copy; that is
        # safe for a file rebuilt from the DB and destructive for anything a
        # person wrote. So adding a prefix must be a deliberate edit HERE,
        # made by someone who has proved the new files are regenerated.
        from divineos.core.substrate_paths import REGENERATED_MIRROR_PREFIXES

        assert REGENERATED_MIRROR_PREFIXES == ("docs/archives/",), (
            "REGENERATED_MIRROR_PREFIXES changed. Before adding a prefix, prove "
            "every file under it is rewritten wholesale from the DB and never "
            "authored by hand -- the checkpoint OVERWRITES their working copy."
        )

    def test_no_restorable_prefix_overlaps_anything_a_person_writes(self):
        from divineos.core.substrate_paths import (
            LOCAL_SUBSTRATE_PREFIXES,
            REGENERATED_MIRROR_PREFIXES,
        )

        authored = [p for p in LOCAL_SUBSTRATE_PREFIXES if p not in REGENERATED_MIRROR_PREFIXES]
        assert authored, "control: there must be authored prefixes to compare against"
        for mirror in REGENERATED_MIRROR_PREFIXES:
            assert mirror in LOCAL_SUBSTRATE_PREFIXES, f"{mirror} is not declared substrate"
            for person in authored:
                assert not mirror.startswith(person) and not person.startswith(mirror), (
                    f"{mirror} overlaps {person}; a restore there could erase a letter"
                )

    def test_on_the_substrate_branch_itself_nothing_changes(self, repo):
        # Standing on the substrate branch, committing here IS committing to
        # substrate. The repair must not alter that path.
        _git(repo, "checkout", "substrate/aether")
        before = _git(repo, "rev-parse", "HEAD")
        (repo / ARCHIVE).write_text("claims v2\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        assert _git(repo, "show", f"substrate/aether:{ARCHIVE}") == "claims v2"
        assert _git(repo, "rev-parse", "HEAD") != before
