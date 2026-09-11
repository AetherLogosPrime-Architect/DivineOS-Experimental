"""The checkpoint saves everything, and stops making someone take it apart.

On 2026-09-03 a checkpoint swept eighteen letters onto a branch carrying
nothing but an anchor fix. The push gate refused it, correctly, and the cure
was a manual three-branch rebuild -- in which the tempting shortcut, dropping
the checkpoint commits and trusting the reflog, risked the only copies of
those letters anywhere in the tree.

``substrate_paths.partition`` was written for this exact call on 2026-08-27 and
then never called: measured, its only importer was its own test, while a second
copy of the same logic grew inside a script. Built, correct, tested, unwired.

These drive the real function against a real repository. The contract pinned
here is narrow and it is the whole point:

  * nothing is excluded and nothing is refused -- the save-work contract that
    makes this safe to run unattended is untouched;
  * the tree still goes clean, so the next checkpoint does not find the same
    files again;
  * when both kinds are present they land in SEPARATE commits, work first, so
    a code branch that picked up letters is trimmed by dropping the tip.

The failure directions matter more than the happy path: every way the split can
fail must fall back to the single commit, because losing the split costs a
manual cleanup and losing the save costs the work itself.

Companion to ``test_auto_commit.py``, which covers the skip conditions and the
external-channel sync.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.auto_commit import auto_commit_substrate
from divineos.core.uncommitted_work_check import ExternalChannel


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "family" / "letters").mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "t@example.com", cwd=root)
    _git("config", "user.name", "t", cwd=root)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "seed", cwd=root)
    # THE DESTINATION MOVED, THE CONTRACTS DID NOT (2026-09-11).
    #
    # These were written against the interim split, which committed BOTH kinds
    # to the checked-out branch -- so substrate landed on the code branch, one
    # commit up from the work, and the fix for a contaminated branch was to
    # drop the tip. The design that superseded it sends substrate to its own
    # branch by plumbing and never touches this one.
    #
    # So every assertion about WHERE substrate landed is rewritten below to ask
    # the substrate branch. Not one assertion about what must be true is
    # relaxed: nothing may be dropped, the tree must still go clean, deletions
    # must still carry, and a broken configuration must still not cost the
    # save. Those got STRONGER, because a file now has to survive a journey
    # between two branches to satisfy them.
    _git("branch", "substrate", cwd=root)
    _git("config", "divineos.substrate-branch", "substrate", cwd=root)
    return root


@pytest.fixture()
def channels(tmp_path):
    """One declared channel whose mirror is the letters directory.

    The source is empty on purpose: the sync copies nothing, so what is under
    test is the partition by mirror rather than the copy.
    """
    source = tmp_path / "shared"
    source.mkdir()
    return (
        ExternalChannel(
            name="letters",
            source=source,
            repo_mirror=Path("family/letters"),
            pattern="*.md",
        ),
    )


def _subjects(root: Path, ref: str = "main") -> list[str]:
    out = _git("log", "--format=%s", ref, cwd=root)
    return [line for line in out.splitlines() if line.strip()]


def _files_in(root: Path, rev: str) -> set[str]:
    out = _git("show", "--name-only", "--format=", rev, cwd=root)
    return {line.strip() for line in out.splitlines() if line.strip()}


def test_both_kinds_land_in_separate_commits_on_their_own_branches(repo, channels):
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "family" / "letters" / "a.md").write_text("dear\n", encoding="utf-8")

    result = auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert result.committed is True
    # Work stays where its author left it: one commit on the checked-out branch.
    subjects = _subjects(repo)
    assert len(subjects) == 2, f"expected one work commit over the seed: {subjects}"
    assert "work in progress" in subjects[0]
    assert _files_in(repo, "HEAD") == {"module.py"}

    # Substrate goes to its declared branch, and the code branch never sees it.
    assert "substrate checkpoint" in _subjects(repo, "substrate")[0]
    assert _files_in(repo, "substrate") == {"family/letters/a.md"}
    assert "family/letters/a.md" not in _files_in(repo, "HEAD")


def test_the_tree_goes_clean_so_the_next_checkpoint_finds_nothing(repo, channels):
    """The save-work contract. A split leaving files behind is worse than none."""
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "family" / "letters" / "a.md").write_text("dear\n", encoding="utf-8")

    auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert _git("status", "--porcelain", cwd=repo) == "", (
        "the checkpoint left files uncommitted; the next one will find them again"
    )
    again = auto_commit_substrate(repo, reason="pre-sleep", channels=channels)
    assert again.committed is False


def test_nothing_is_dropped_when_both_kinds_are_present(repo, channels):
    """Everything staged lands in one of the two commits. No path may vanish."""
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "other.py").write_text("y = 2\n", encoding="utf-8")
    for n in ("a", "b", "c"):
        (repo / "family" / "letters" / f"{n}.md").write_text(n, encoding="utf-8")

    auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    # The union spans BOTH branches now, which is the stronger version of this
    # assertion: a file has to survive the journey to its own branch to be here.
    landed = _files_in(repo, "HEAD") | _files_in(repo, "substrate")
    assert landed == {
        "module.py",
        "other.py",
        "family/letters/a.md",
        "family/letters/b.md",
        "family/letters/c.md",
    }


def test_substrate_only_leaves_the_code_branch_untouched(repo, channels):
    (repo / "family" / "letters" / "a.md").write_text("dear\n", encoding="utf-8")

    result = auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert result.committed is True
    # Nothing to save on this branch, so nothing is written to it at all --
    # the stronger form of "stays one commit" under the retargeting design.
    assert _subjects(repo) == ["seed"]
    assert "substrate checkpoint" in _subjects(repo, "substrate")[0]
    assert _files_in(repo, "substrate") == {"family/letters/a.md"}


def test_work_only_says_work_rather_than_calling_itself_substrate(repo, channels):
    """The old subject called every checkpoint a substrate one, including those
    carrying no substrate at all. A commit whose subject misnames its contents
    is what made the queue hard to read at a glance."""
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")

    auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert "work in progress" in _subjects(repo)[0]


def test_a_broken_channel_config_still_saves_the_work(repo):
    """A broken configuration must not cost the save.

    ``partition`` raises rather than classifying everything as work when no
    channel is declared -- correctly, because those two are indistinguishable
    at the call site. The checkpoint has to catch that and commit anyway.
    """
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "family" / "letters" / "a.md").write_text("dear\n", encoding="utf-8")

    result = auto_commit_substrate(repo, reason="pre-extract", channels=())

    assert result.committed is True, "a broken channel config swallowed the work"
    assert _git("status", "--porcelain", cwd=repo) == ""

    # THE BROKEN CONFIG GOT LESS COSTLY, NOT MORE (2026-09-11).
    #
    # This used to assert both files landed together on the code branch, which
    # was the honest fallback when classification was impossible. It is no
    # longer impossible: the four local prefixes classify a letter with no
    # channel declared at all, which is the whole reason that list exists --
    # a derived list cannot see substrate that arrives without a declaration.
    #
    # So a broken channel config no longer mislabels a letter as work and
    # leaves it on the code branch. The save-work contract is intact and the
    # letter reaches the same place it would have with a working config.
    assert _files_in(repo, "HEAD") == {"module.py"}
    assert _files_in(repo, "substrate") == {"family/letters/a.md"}, (
        "the letter was neither committed here nor retargeted -- a broken "
        "channel config swallowed it, which is the one thing this forbids"
    )


def test_a_deleted_substrate_file_is_still_split_correctly(repo, channels):
    """Deletions are staged too, and a pathspec reset has to carry them.

    Written because the split unstages by pathspec and then restages by
    pathspec, and a deletion is the case where those two operations are least
    alike -- `git add` on a removed path has to be told the path still counts.
    """
    letter = repo / "family" / "letters" / "old.md"
    letter.write_text("old\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "letter", cwd=repo)

    letter.unlink()
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")

    auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert _git("status", "--porcelain", cwd=repo) == "", (
        "the deletion was not carried through the split and is still pending"
    )
    # Each commit checked SEPARATELY, and the union would not do. The union
    # holds both paths even when no split happened at all -- an unsplit
    # checkpoint lands both in one commit, and the letter's own earlier commit
    # supplies the rest -- so this assertion was green against code that had
    # never heard of the split. Found by the pin checker, which exists for
    # exactly this: a test whose docstring names the behaviour it pins while
    # its assertion cannot tell that behaviour from its absence.
    # THE DELETION IS COMMITTED HERE, ON PURPOSE, AND THAT IS THE REPAIR.
    #
    # This letter was already TRACKED on the code branch -- contamination from
    # a sweep that predates the retargeting design. Routing its deletion to the
    # substrate branch would record the change on a ref this branch cannot see
    # while this branch still tracks the file, so the pending deletion would
    # never clear and no checkpoint would ever make the tree clean again.
    #
    # Committing it here reads like a retreat to the old contamination and is
    # the opposite: this commit is precisely what takes the letter OFF the code
    # branch. What it does not fix is the history, which still carries the
    # letter, and the checkpoint says so by name every time.
    assert _files_in(repo, "HEAD") == {"family/letters/old.md", "module.py"}, (
        "the deletion of an already-tracked letter was not carried here, so "
        "the tree can never go clean"
    )
    assert not (repo / "family" / "letters" / "old.md").exists()
    # And the point of carrying it: the letter is no longer IN this branch's
    # tree. `cat-file -e` exits non-zero when the path is absent from the rev,
    # which is the whole claim -- committing the deletion evicted it.
    gone = subprocess.run(
        ["git", "cat-file", "-e", "HEAD:family/letters/old.md"],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    assert gone.returncode != 0, (
        "the letter is still in the code branch's tree; the deletion was "
        "recorded but the branch still carries it"
    )


def _warnings_said(caplog) -> str:
    # ``getMessage()`` and not ``r.message % r.args``: the hand-rolled version
    # raised TypeError on an unrelated record whose template consumed fewer
    # args than it carried. Formatting a log record is the logging module's
    # job and it already knows how.
    return "\n".join(r.getMessage() for r in caplog.records)


def test_the_split_says_so_while_the_tip_can_still_be_trimmed(repo, channels, caplog):
    """The affordance is real and it was silent, so it kept expiring unused.

    Substrate is committed LAST on purpose: a code branch that picked up
    letters can then be fixed by dropping the tip rather than rebuilt. That
    works only while the substrate commit IS the tip, and nothing said so — so
    on 2026-09-10 it happened three times, and each time the push gate refused
    the branch long afterwards, by which point another commit sat on top and
    the one-line cure had become surgery with a written justification.

    The warning decides nothing new. It makes the consequence of a split that
    already ran arrive while it can still be acted on.
    """
    import logging

    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "family" / "letters" / "swept.md").write_text("dear\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="divineos.core.auto_commit"):
        auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    # THE WARNING IS GONE BECAUSE THE CONDITION IS, and that claim is the test.
    #
    # Deleting a protection because a redesign "makes it impossible" is how a
    # guard quietly becomes an assumption. So this no longer asserts the
    # warning fired -- it asserts the thing the warning existed to announce
    # cannot happen: substrate does not reach the code branch at all, so there
    # is no tip to trim and nothing to say. If a later change puts substrate
    # back on this branch, this fails rather than going quietly green.
    said = _warnings_said(caplog)
    assert "swept.md" not in _files_in(repo, "HEAD"), (
        "substrate landed on the code branch; the tip warning was removed on "
        "the grounds that this cannot happen, and it just did"
    )
    assert _files_in(repo, "substrate") == {"family/letters/swept.md"}
    assert "TIP" not in said, (
        "a tip warning fired for a split that no longer lands substrate on the tip"
    )


def test_it_also_says_the_commit_underneath_is_not_safe_to_drop(repo, channels, caplog):
    """The half the first version left out, found by acting on the first half.

    The warning said drop the tip. I dropped the tip AND the commit under it,
    which held two script files swept mid-edit -- so my own later commit of
    those paths found no diff and carried only a test. Four commits and a full
    suite later the push failed on a test whose subject had silently reverted.

    The asymmetry is the whole content: substrate on the tip exists in the
    shared channel and is safe to drop; the work checkpoint beneath it may be
    the only copy of edits the session never committed itself.
    """
    import logging

    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "family" / "letters" / "swept.md").write_text("dear\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="divineos.core.auto_commit"):
        auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    # The asymmetry this pinned is unchanged and is now structural rather than
    # advisory: the work checkpoint is the tip, and no instruction to drop a
    # tip is emitted any more, so the way to lose it by following advice is
    # gone. What is pinned here is that the only-copy commit is still MADE and
    # still sits where its author can see it.
    said = _warnings_said(caplog)
    assert _files_in(repo, "HEAD") == {"module.py"}, (
        "the work checkpoint -- possibly the only copy of these edits -- was "
        "not made, or did not land on the branch its author is standing on"
    )
    assert "reset --soft" not in said, (
        "something still advises dropping a tip; that advice is what cost the "
        "only copy of two script files, and the split it referred to is gone"
    )
    assert "BELOW" not in said, (
        "it named the commit without naming the stakes; 'do not drop this' is "
        "advice, 'this may be the only copy' is a reason"
    )


def test_a_work_only_checkpoint_says_nothing_about_tips(repo, channels, caplog):
    """Control. Without it, the assertions above pass on a warning that fires
    every time — which is the shape that turns a signal into furniture."""
    import logging

    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="divineos.core.auto_commit"):
        auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert "TIP" not in _warnings_said(caplog), (
        "it warned about substrate on a checkpoint carrying none"
    )
