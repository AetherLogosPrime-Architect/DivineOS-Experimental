"""A regenerated mirror skipped on a non-owning branch is restored, so the tree stays clean.

Main already keeps docs/archives/* off code branches (measured 2026-09-30:
PR #547's own tests, 5 of 8 pass on main once origin/HEAD is set). What main
does not do is leave the tree clean: the skipped mirror stays modified on disk
at every checkpoint, forever. Restoring it to HEAD loses nothing, because the
export is reproducible (export_all run twice: identical, timestamp aside) and
the DB holds the content.

Restoring is an OVERWRITE, which is safe for a mirror and destroys a letter's
only copy (Aria, station 3). So the restorable set is its own constant,
asserted at import to be inside the mirror set and disjoint from every
authored prefix, and paths are checked normalised (Knuth and Schneier,
walk-d8f579d59dec). And the restore stands down when this branch is itself
changing the archives or their generator, because there the dirty file is the
PR's evidence (Penrose, Yudkowsky, Dawkins).

Existing mirror tests (test_a_mirror_that_rebuilds_itself_rides_one_branch.py)
pin only what counts as a mirror; none pins the dirty-tree behaviour this
changes. The first test failed on main at e481bdd30. prereg-ecac53dcdea3.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.auto_commit import auto_commit_substrate

ARCHIVE = "docs/archives/claims.md"
GENERATOR = "src/divineos/core/archive_export.py"
LETTER = "family/letters/aether-to-aria-2026-09-30-a-letter.md"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """main tracks an archive and owns it via origin/HEAD; a code branch is checked out."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-b", "main")
    _git(r, "config", "user.email", "test@example.com")
    _git(r, "config", "user.name", "Test")
    (r / "docs" / "archives").mkdir(parents=True)
    (r / ARCHIVE).write_text("claims v1\n", encoding="utf-8")
    (r / "src" / "divineos" / "core").mkdir(parents=True)
    (r / GENERATOR).write_text("VERSION = 1\n", encoding="utf-8")
    (r / "tracked_code.py").write_text("x = 1\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-m", "seed")
    bare = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(bare))
    _git(r, "remote", "add", "origin", str(bare))
    _git(r, "push", "-q", "origin", "main")
    _git(r, "remote", "set-head", "origin", "main")
    _git(r, "branch", "substrate/aether")
    _git(r, "config", "divineos.substrate-branch", "substrate/aether")
    _git(r, "checkout", "-b", "fix/some-code-change")
    return r


def _status(repo: Path, path: str) -> str:
    return _git(repo, "status", "--short", "--", path)


class TestTheTreeIsLeftClean:
    def test_a_skipped_mirror_is_restored_on_a_code_branch(self, repo):
        before = _git(repo, "rev-parse", "HEAD")
        (repo / ARCHIVE).write_text("claims v2, regenerated from the DB\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        assert _status(repo, ARCHIVE) == "", "the skipped mirror was left modified on disk"
        assert ARCHIVE not in _git(repo, "diff", "--name-only", before, "HEAD").splitlines()

    def test_tracked_code_is_still_saved(self, repo):
        before = _git(repo, "rev-parse", "HEAD")
        (repo / "tracked_code.py").write_text("x = 2  # half done\n", encoding="utf-8")
        (repo / ARCHIVE).write_text("claims v2\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        changed = _git(repo, "diff", "--name-only", before, "HEAD").splitlines()
        assert "tracked_code.py" in changed
        assert ARCHIVE not in changed


class TestItStandsDownWhenTheBranchIsTheChange:
    def test_a_branch_that_changes_the_generator_keeps_its_new_archive(self, repo):
        (repo / GENERATOR).write_text("VERSION = 2\n", encoding="utf-8")
        _git(repo, "commit", "-qam", "new archive format")
        (repo / ARCHIVE).write_text("claims in the new format\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        assert (repo / ARCHIVE).read_text(encoding="utf-8") == "claims in the new format\n"

    def test_a_branch_that_commits_an_archive_change_keeps_it(self, repo):
        (repo / ARCHIVE).write_text("claims, hand-fixed on this branch\n", encoding="utf-8")
        _git(repo, "commit", "-qam", "fix archive by hand")
        (repo / ARCHIVE).write_text("claims, regenerated after\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        assert (repo / ARCHIVE).read_text(encoding="utf-8") == "claims, regenerated after\n"


class TestItNeverTouchesWhatAPersonWrote:
    def test_a_new_letter_keeps_its_only_copy(self, repo):
        # An untracked letter is retargeted to the substrate branch and leaves
        # the code branch's tree; that is the existing, correct behaviour. What
        # must hold is that its words survive somewhere -- never reverted.
        (repo / "family" / "letters").mkdir(parents=True)
        (repo / LETTER).write_text("only copy\n", encoding="utf-8")
        (repo / ARCHIVE).write_text("claims v2\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        on_disk = (repo / LETTER).read_text(encoding="utf-8") if (repo / LETTER).exists() else None
        on_substrate = _git(repo, "show", f"substrate/aether:{LETTER}")
        assert on_disk == "only copy\n" or on_substrate == "only copy"

    def test_a_tracked_letter_edit_is_never_reverted(self, repo):
        (repo / "family" / "letters").mkdir(parents=True)
        (repo / LETTER).write_text("first draft\n", encoding="utf-8")
        _git(repo, "add", LETTER)
        _git(repo, "commit", "-qm", "letter stranded on the code branch")
        (repo / LETTER).write_text("first draft, and the part that matters\n", encoding="utf-8")
        (repo / ARCHIVE).write_text("claims v2\n", encoding="utf-8")

        auto_commit_substrate(repo, reason="pre-extract", channels=())

        assert (repo / LETTER).read_text(
            encoding="utf-8"
        ) == "first draft, and the part that matters\n" or "the part that matters" in _git(
            repo, "show", f"HEAD:{LETTER}"
        )

    def test_the_restorable_set_is_inside_mirrors_and_outside_everything_authored(self):
        from divineos.core.substrate_paths import (
            LOCAL_SUBSTRATE_PREFIXES,
            REGENERATED_MIRROR_PREFIXES,
            RESTORABLE_MIRROR_PREFIXES,
        )

        assert RESTORABLE_MIRROR_PREFIXES == ("docs/archives/",), (
            "the restore OVERWRITES working copies; widen this only after proving "
            "every file under the new prefix is rebuilt wholesale from a DB"
        )
        authored = [p for p in LOCAL_SUBSTRATE_PREFIXES if p not in REGENERATED_MIRROR_PREFIXES]
        assert authored, "control: there must be authored prefixes to compare against"
        for r in RESTORABLE_MIRROR_PREFIXES:
            assert r in REGENERATED_MIRROR_PREFIXES
            for person in authored:
                assert not r.startswith(person) and not person.startswith(r)

    @pytest.mark.parametrize(
        "path",
        [
            "docs/archives/../../family/letters/x.md",
            "docs/archives/../exploration/x.md",
            "/docs/archives/claims.md",
            "family/letters/docs/archives/claims.md",
            "docs/archives/",
            "",
        ],
    )
    def test_a_path_that_only_looks_like_an_archive_is_not_restorable(self, path):
        from divineos.core.substrate_paths import is_restorable_mirror

        assert not is_restorable_mirror(path)

    def test_a_real_archive_path_is_restorable_in_either_slash(self):
        from divineos.core.substrate_paths import is_restorable_mirror

        assert is_restorable_mirror("docs/archives/claims.md")
        assert is_restorable_mirror("docs\\archives\\claims.md")
